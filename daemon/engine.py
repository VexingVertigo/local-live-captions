import os
import sys

# Register nvidia CUDA DLL directories on Windows for CTranslate2
if sys.platform == "win32":
    site_packages = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".venv", "Lib", "site-packages")
    cuda_dirs = [
        os.path.join(site_packages, "nvidia", "cublas", "bin"),
        os.path.join(site_packages, "nvidia", "cudnn", "bin"),
        os.path.join(site_packages, "torch", "lib")
    ]
    for p in cuda_dirs:
        if os.path.exists(p):
            os.add_dll_directory(p)
            os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")

import numpy as np
from faster_whisper import WhisperModel

class StreamingASREngine:
    def __init__(self, model_size: str = "large-v3-turbo"):
        print(f"[Engine] Loading faster-whisper ({model_size}) onto CUDA...")
        self.model = WhisperModel(
            model_size,
            device="cuda",
            compute_type="float16"
        )

        self.sample_rate = 16000
        self.buffer = np.zeros(0, dtype=np.float32)

        # 1.5-second chunk (~24,000 samples)
        self.chunk_size = int(self.sample_rate * 1.5)
        print(f"[Engine] Whisper {model_size} ready in VRAM.")

    def process_audio_chunk(self, audio_data: np.ndarray) -> str:
        if len(audio_data) == 0:
            return ""

        chunk_raw = np.asarray(audio_data, dtype=np.float32)
        self.buffer = np.append(self.buffer, chunk_raw)

        if len(self.buffer) < self.chunk_size:
            return ""

        audio_to_process = self.buffer[:self.chunk_size].copy()
        self.buffer = self.buffer[self.chunk_size:]

        # Skip silence before calling GPU
        rms = float(np.sqrt(np.mean(audio_to_process ** 2)))
        if rms < 0.003:
            return ""

        try:
            segments, _ = self.model.transcribe(
                audio_to_process,
                language="en",
                beam_size=1,
                temperature=0.0,
                condition_on_previous_text=False,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300)
            )

            text = " ".join([seg.text.strip() for seg in segments if seg.text.strip()])
            return text

        except Exception as e:
            print(f"[Whisper Error] {e}")
            return ""