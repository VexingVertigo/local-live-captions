import numpy as np
from faster_whisper import WhisperModel
from .base import BaseASREngine


class WhisperASREngine(BaseASREngine):
    tier_name = "balanced"

    def __init__(self, model_name: str = "large-v3-turbo", force_cpu: bool = False):
        super().__init__(force_cpu=force_cpu, enable_diarization=True)
        self.model_name = model_name
        self.compute_type = "float16" if self.device == "cuda" else "int8"

        print(f"[Engine:balanced] Starting Whisper ({model_name}) on {self.device.upper()} [{self.compute_type}]...")
        try:
            self.asr = WhisperModel(model_name, device=self.device, compute_type=self.compute_type)
        except Exception as e:
            print(f"[Engine Warning] GPU initialization failed ({e}). Falling back to CPU...")
            self.device, self.compute_type = "cpu", "int8"
            self.asr = WhisperModel(model_name, device="cpu", compute_type="int8")

        self.min_chunk_samples = int(self.sample_rate * 1.2)
        self.max_buffer_samples = int(self.sample_rate * 2.5)
        print("[Engine:balanced] Clean VAD clause engine ready.")

    def process_audio_chunk(self, audio_input, session_id: str = "default"):
        session = self.get_or_create_session(session_id)
        chunk_raw = self.normalize_audio(audio_input)
        if len(chunk_raw) == 0:
            return None

        session.audio_buffer = np.append(session.audio_buffer, chunk_raw)
        if len(session.audio_buffer) < self.min_chunk_samples:
            return None

        try:
            segments, _ = self.asr.transcribe(
                session.audio_buffer,
                language="en",
                beam_size=1,
                temperature=0.0,
                condition_on_previous_text=False,
                repetition_penalty=1.15,
                no_repeat_ngram_size=3,
                compression_ratio_threshold=1.8,
                no_speech_threshold=0.6,
                vad_filter=True,
                vad_parameters=dict(
                    threshold=0.5,
                    min_silence_duration_ms=300,
                    speech_pad_ms=150,
                ),
            )

            text = " ".join(seg.text.strip() for seg in segments if seg.text.strip())
            if not text:
                session.audio_buffer = np.zeros(0, dtype=np.float32)
                return None

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
            print(f"[Engine:balanced Error] {e}")
            session.audio_buffer = np.zeros(0, dtype=np.float32)
            return None