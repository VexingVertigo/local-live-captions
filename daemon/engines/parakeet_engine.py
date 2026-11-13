import numpy as np
import onnx_asr
from .base import BaseASREngine


class ParakeetASREngine(BaseASREngine):
    tier_name = "lite"

    def __init__(self, model_name: str = "nemo-parakeet-tdt-0.6b-v2", force_cpu: bool = False):
        # Disable heavy NeMo diarization in lite mode to keep CPU/low-VRAM footprint minimal
        super().__init__(force_cpu=force_cpu, enable_diarization=False)
        self.model_name = model_name

        providers = ["CPUExecutionProvider"] if self.device == "cpu" else ["CUDAExecutionProvider", "CPUExecutionProvider"]
        quant = "int8" if self.device == "cpu" else None

        print(f"[Engine:lite] Loading ONNX Parakeet ({model_name}) on {self.device.upper()}...")
        self.asr = onnx_asr.load_model(model_name, quantization=quant, providers=providers)

        self.min_chunk_samples = int(self.sample_rate * 1.0)
        self.max_buffer_samples = int(self.sample_rate * 2.2)
        self.rms_silence_threshold = 0.008
        print("[Engine:lite] Parakeet TDT ONNX engine ready.")

    def process_audio_chunk(self, audio_input, session_id: str = "default"):
        session = self.get_or_create_session(session_id)
        chunk_raw = self.normalize_audio(audio_input)
        if len(chunk_raw) == 0:
            return None

        session.audio_buffer = np.append(session.audio_buffer, chunk_raw)
        if len(session.audio_buffer) < self.min_chunk_samples:
            return None

        # Fast RMS energy gate so silence isn't decoded unnecessarily
        rms = float(np.sqrt(np.mean(np.square(session.audio_buffer))))
        if rms < self.rms_silence_threshold:
            session.audio_buffer = np.zeros(0, dtype=np.float32)
            return None

        # Check trailing 250ms energy to detect natural inter-word/clause pauses
        tail_samples = int(self.sample_rate * 0.25)
        tail_rms = float(np.sqrt(np.mean(np.square(session.audio_buffer[-tail_samples:]))))
        has_trailing_silence = tail_rms < self.rms_silence_threshold
        is_buffer_full = len(session.audio_buffer) >= self.max_buffer_samples

        if not (has_trailing_silence or is_buffer_full):
            return None

        try:
            raw_out = self.asr.recognize(session.audio_buffer)
            text = raw_out.strip() if isinstance(raw_out, str) else str(raw_out).strip()

            session.audio_buffer = np.zeros(0, dtype=np.float32)
            if not text or text.lower() == session.last_emitted_text.lower():
                return None

            session.last_emitted_text = text
            print(f"[ASR:lite ({session_id})] -> \"{text}\"")
            return {"text": text, "speaker": 0}
        except Exception as e:
            print(f"[Engine:lite Error] {e}")
            session.audio_buffer = np.zeros(0, dtype=np.float32)
            return None