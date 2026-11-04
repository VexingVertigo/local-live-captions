import os
import sys
import numpy as np
import torch

# Register CUDA DLLs on Windows
if sys.platform == "win32":
    site_packages = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".venv", "Lib", "site-packages")
    cuda_dirs = [
        os.path.join(site_packages, "nvidia", "cublas", "bin"),
        os.path.join(site_packages, "torch", "lib")
    ]
    for p in cuda_dirs:
        if os.path.exists(p):
            os.add_dll_directory(p)
            os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")

torch.backends.cudnn.enabled = False

from faster_whisper import WhisperModel

try:
    import nemo.collections.asr as nemo_asr
    NEMO_AVAILABLE = True
except ImportError:
    NEMO_AVAILABLE = False


class ClientSession:
    def __init__(self):
        self.audio_buffer = np.zeros(0, dtype=np.float32)
        self.last_emitted_text = ""
        self.speaker_centroids = []
        self.current_speaker = 0


class StreamingASREngine:
    def __init__(self, whisper_model: str = "large-v3-turbo", force_cpu: bool = False):
        use_cuda = torch.cuda.is_available() and not force_cpu
        self.device = "cuda" if use_cuda else "cpu"
        self.compute_type = "float16" if use_cuda else "int8"
        self.torch_device = torch.device(self.device)

        print(f"[Engine] Starting Whisper ({whisper_model}) on {self.device.upper()} [{self.compute_type}]...")
        try:
            self.asr = WhisperModel(whisper_model, device=self.device, compute_type=self.compute_type)
        except Exception as e:
            print(f"[Engine Warning] GPU initialization failed ({e}). Falling back to CPU...")
            self.device, self.compute_type = "cpu", "int8"
            self.torch_device = torch.device("cpu")
            self.asr = WhisperModel(whisper_model, device="cpu", compute_type="int8")

        self.speaker_model = None
        if NEMO_AVAILABLE:
            try:
                print(f"[Engine] Loading ECAPA-TDNN Speaker Diarizer on {self.torch_device}...")
                self.speaker_model = nemo_asr.models.EncDecSpeakerLabelModel.from_pretrained(model_name="ecapa_tdnn")
                self.speaker_model = self.speaker_model.to(self.torch_device)
                self.speaker_model.eval()
            except Exception as e:
                print(f"[Engine Warning] Diarizer load failed ({e}). Running single-speaker mode.")

        self.sample_rate = 16000
        # 1.2s minimum speech slice, 2.5s max clause buffer
        self.min_chunk_samples = int(self.sample_rate * 1.2)
        self.max_buffer_samples = int(self.sample_rate * 2.5)
        self.max_speakers = 4
        self.similarity_threshold = 0.60
        self.sessions = {}
        print(f"[Engine] Clean VAD clause engine ready.")

    def get_or_create_session(self, session_id: str) -> ClientSession:
        if session_id not in self.sessions:
            self.sessions[session_id] = ClientSession()
        return self.sessions[session_id]

    def remove_session(self, session_id: str):
        self.sessions.pop(session_id, None)

    def _identify_speaker(self, session: ClientSession, audio_chunk: np.ndarray) -> int:
        if self.speaker_model is None or len(audio_chunk) < int(self.sample_rate * 0.6):
            return session.current_speaker

        try:
            with torch.inference_mode():
                tensor = torch.from_numpy(audio_chunk).float().to(self.torch_device).unsqueeze(0)
                length = torch.tensor([audio_chunk.shape[0]], device=self.torch_device)

                _, emb = self.speaker_model(input_signal=tensor, input_signal_length=length)
                emb_np = emb.squeeze().detach().cpu().numpy().flatten()

                norm = np.linalg.norm(emb_np)
                if norm < 1e-6:
                    return session.current_speaker
                emb_np /= norm

                if not session.speaker_centroids:
                    session.speaker_centroids.append(emb_np)
                    session.current_speaker = 0
                    return 0

                sims = np.dot(session.speaker_centroids, emb_np)
                best_idx = int(np.argmax(sims))
                best_sim = float(sims[best_idx])

                if best_sim >= self.similarity_threshold:
                    updated = 0.85 * session.speaker_centroids[best_idx] + 0.15 * emb_np
                    session.speaker_centroids[best_idx] = updated / np.linalg.norm(updated)
                    session.current_speaker = best_idx
                elif len(session.speaker_centroids) < self.max_speakers:
                    session.current_speaker = len(session.speaker_centroids)
                    session.speaker_centroids.append(emb_np)
                else:
                    session.current_speaker = best_idx

                return session.current_speaker
        except Exception:
            return session.current_speaker

    def process_audio_chunk(self, audio_input, session_id: str = "default"):
        session = self.get_or_create_session(session_id)

        # 1. Downmix stereo and cast to 16kHz float32 mono
        if isinstance(audio_input, (bytes, bytearray)):
            chunk_raw = np.frombuffer(audio_input, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            chunk_raw = np.asarray(audio_input, dtype=np.float32)
            if chunk_raw.ndim == 2:
                chunk_raw = np.mean(chunk_raw, axis=1)

        if len(chunk_raw) == 0:
            return None

        session.audio_buffer = np.append(session.audio_buffer, chunk_raw)

        # Wait until minimum audio buffer is accumulated
        if len(session.audio_buffer) < self.min_chunk_samples:
            return None

        # 2. Transcribe accumulated clause with Silero VAD & repetition suppression
        try:
            segments, info = self.asr.transcribe(
                session.audio_buffer,
                language="en",
                beam_size=1,
                temperature=0.0,
                condition_on_previous_text=False,
                repetition_penalty=1.15,          # Prevents autoregressive looping on background music/noise
                no_repeat_ngram_size=3,            # Strictly forbids 3x word repetitions
                compression_ratio_threshold=1.8,   # Discards repetitive hallucination loops
                no_speech_threshold=0.6,
                vad_filter=True,
                vad_parameters=dict(
                    threshold=0.5,
                    min_silence_duration_ms=300,
                    speech_pad_ms=150
                )
            )

            text = " ".join(seg.text.strip() for seg in segments if seg.text.strip())

            # If pure silence detected by VAD
            if not text:
                session.audio_buffer = np.zeros(0, dtype=np.float32)
                return None

            # Check if speaker finished a thought (pause/punctuation) or if buffer reached max window
            has_pause = text.endswith((".", "?", "!", ",", "..."))
            is_buffer_full = len(session.audio_buffer) >= self.max_buffer_samples

            if has_pause or is_buffer_full:
                if text.lower() == session.last_emitted_text.lower():
                    session.audio_buffer = np.zeros(0, dtype=np.float32)
                    return None

                speaker = self._identify_speaker(session, session.audio_buffer)
                session.last_emitted_text = text
                session.audio_buffer = np.zeros(0, dtype=np.float32)

                print(f"[ASR ({session_id})] -> \"{text}\" (Speaker {speaker})")
                return {"text": text, "speaker": speaker}

            return None

        except Exception as e:
            print(f"[Engine Error] {e}")
            session.audio_buffer = np.zeros(0, dtype=np.float32)
            return None