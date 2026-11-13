import os
import sys
import numpy as np
import torch

# Register CUDA DLLs on Windows
if sys.platform == "win32":
    site_packages = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        ".venv",
        "Lib",
        "site-packages",
    )
    cuda_dirs = [
        os.path.join(site_packages, "nvidia", "cublas", "bin"),
        os.path.join(site_packages, "torch", "lib"),
    ]
    for p in cuda_dirs:
        if os.path.exists(p):
            os.add_dll_directory(p)
            os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")

torch.backends.cudnn.enabled = False

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
        # Optional backend-specific streaming state (used by Kyutai STT)
        self.stream_state = None


class BaseASREngine:
    tier_name = "base"
    model_name = "unknown"

    def __init__(self, force_cpu: bool = False, enable_diarization: bool = True):
        use_cuda = torch.cuda.is_available() and not force_cpu
        self.device = "cuda" if use_cuda else "cpu"
        self.torch_device = torch.device(self.device)
        self.sample_rate = 16000
        self.max_speakers = 4
        self.similarity_threshold = 0.60
        self.sessions: dict[str, ClientSession] = {}

        self.speaker_model = None
        if enable_diarization and NEMO_AVAILABLE:
            try:
                print(f"[Engine] Loading ECAPA-TDNN Speaker Diarizer on {self.torch_device}...")
                self.speaker_model = nemo_asr.models.EncDecSpeakerLabelModel.from_pretrained(
                    model_name="ecapa_tdnn"
                )
                self.speaker_model = self.speaker_model.to(self.torch_device)
                self.speaker_model.eval()
            except Exception as e:
                print(f"[Engine Warning] Diarizer load failed ({e}). Running single-speaker mode.")

    def get_or_create_session(self, session_id: str) -> ClientSession:
        if session_id not in self.sessions:
            self.sessions[session_id] = ClientSession()
        return self.sessions[session_id]

    def remove_session(self, session_id: str):
        self.sessions.pop(session_id, None)

    @staticmethod
    def normalize_audio(audio_input) -> np.ndarray:
        """Downmixes stereo and normalizes incoming bytes or arrays to 16kHz float32 mono."""
        if isinstance(audio_input, (bytes, bytearray)):
            chunk = np.frombuffer(audio_input, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            chunk = np.asarray(audio_input, dtype=np.float32)
            if chunk.ndim == 2:
                chunk = np.mean(chunk, axis=1)
        return chunk

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
        raise NotImplementedError