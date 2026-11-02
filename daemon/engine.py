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
import nemo.collections.asr as nemo_asr


class ClientSession:
    def __init__(self):
        self.buffer = np.zeros(0, dtype=np.float32)
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

        print(f"[Engine] Loading ECAPA-TDNN Speaker Diarizer on {self.torch_device}...")
        self.speaker_model = nemo_asr.models.EncDecSpeakerLabelModel.from_pretrained(model_name="ecapa_tdnn")
        self.speaker_model = self.speaker_model.to(self.torch_device)
        self.speaker_model.eval()

        self.sample_rate = 16000
        self.chunk_size = int(self.sample_rate * 1.5)
        self.max_speakers = 4
        self.similarity_threshold = 0.60

        # Isolated sessions dictionary: session_id -> ClientSession
        self.sessions = {}
        print(f"[Engine] Engine online and ready.")

    def get_or_create_session(self, session_id: str) -> ClientSession:
        if session_id not in self.sessions:
            self.sessions[session_id] = ClientSession()
        return self.sessions[session_id]

    def remove_session(self, session_id: str):
        self.sessions.pop(session_id, None)

    def _identify_speaker(self, session: ClientSession, audio_chunk: np.ndarray) -> int:
        if len(audio_chunk) < int(self.sample_rate * 0.4):
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

        except Exception as e:
            if self.torch_device != torch.device("cpu"):
                print(f"[Diarizer Warning] GPU error ({e}). Shifting Diarizer to CPU...")
                self.torch_device = torch.device("cpu")
                self.speaker_model = self.speaker_model.to(self.torch_device)
                return self._identify_speaker(session, audio_chunk)
            return session.current_speaker

    def process_audio_chunk(self, audio_input, session_id: str = "default"):
        session = self.get_or_create_session(session_id)

        # Convert incoming data: handle raw bytes (PCM 16-bit mono from Android) or float32 np.ndarray
        if isinstance(audio_input, (bytes, bytearray)):
            chunk_raw = np.frombuffer(audio_input, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            chunk_raw = np.asarray(audio_input, dtype=np.float32)

        if len(chunk_raw) == 0:
            return None

        session.buffer = np.append(session.buffer, chunk_raw)
        if len(session.buffer) < self.chunk_size:
            return None

        chunk = session.buffer[:self.chunk_size].copy()
        session.buffer = session.buffer[self.chunk_size:]

        # Skip silence
        if float(np.sqrt(np.mean(chunk ** 2))) < 0.003:
            return None

        try:
            segments, _ = self.asr.transcribe(
                chunk,
                language="en",
                beam_size=1,
                temperature=0.0,
                condition_on_previous_text=False,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300)
            )

            text = " ".join(seg.text.strip() for seg in segments if seg.text.strip())
            if not text:
                return None

            return {"text": text, "speaker": self._identify_speaker(session, chunk)}

        except Exception as e:
            print(f"[Whisper Error] {e}")
            return None