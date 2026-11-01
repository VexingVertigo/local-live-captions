import difflib
import torch
import numpy as np
import nemo.collections.asr as nemo_asr

class StreamingASREngine:
    def __init__(self, model_name: str = "stt_en_fastconformer_hybrid_large_streaming_80ms"):
        print(f"[Engine] Loading streaming ASR model ({model_name}) onto cuda...")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = nemo_asr.models.EncDecHybridRNNTCTCBPEModel.from_pretrained(model_name=model_name)
        self.model = self.model.to(self.device)
        self.model.eval()

        self.sample_rate = 16000
        self.buffer = np.zeros(0, dtype=np.float32)

        # 1.8-second window with 0.6-second sliding step
        self.window_samples = int(self.sample_rate * 1.8)
        self.step_samples = int(self.sample_rate * 0.6)

        self.last_decoded_words = []
        print("[Engine] Streaming ASR model successfully loaded into VRAM.")

    def _align_and_deduplicate(self, new_text: str, is_silence_at_end: bool) -> str:
        words = new_text.strip().split()
        if not words:
            return ""

        # If speech is ongoing mid-word at the window boundary, hold back the last word
        # so it gets transcribed with complete phonetic context in the next slice.
        if not is_silence_at_end and len(words) > 1:
            words = words[:-1]

        if not self.last_decoded_words:
            self.last_decoded_words = words
            return " ".join(words)

        prev_lower = [w.lower() for w in self.last_decoded_words]
        new_lower = [w.lower() for w in words]

        # Find best overlap match between preceding tail and current head
        matcher = difflib.SequenceMatcher(None, prev_lower, new_lower)
        match = matcher.find_longest_match(0, len(prev_lower), 0, len(new_lower))

        if match.size >= 1 and (match.a + match.size >= len(prev_lower) - 1):
            new_start_idx = match.b + match.size
            emitted_words = words[new_start_idx:]
        else:
            emitted_words = words

        self.last_decoded_words = words
        return " ".join(emitted_words)

    def process_audio_chunk(self, audio_data: np.ndarray) -> str:
        if len(audio_data) == 0:
            return ""

        rms = float(np.sqrt(np.mean(audio_data ** 2)))

        # Flush buffer if there has been silence
        if rms < 0.002:
            if len(self.buffer) >= self.window_samples:
                self.buffer = np.zeros(0, dtype=np.float32)
                self.last_decoded_words = []
                return ""

        self.buffer = np.append(self.buffer, audio_data)

        if len(self.buffer) < self.window_samples:
            return ""

        chunk = self.buffer[:self.window_samples].copy()
        self.buffer = self.buffer[self.step_samples:]

        # Detect if speaker paused at the tail end of the chunk
        tail_audio = chunk[-int(self.sample_rate * 0.2):]
        tail_rms = float(np.sqrt(np.mean(tail_audio ** 2)))
        is_silence_at_end = tail_rms < 0.003

        try:
            with torch.inference_mode():
                res = self.model.transcribe([chunk], verbose=False)
                if not res or len(res) == 0:
                    return ""

                item = res[0]
                if isinstance(item, (list, tuple)) and len(item) > 0:
                    item = item[0]

                raw_text = getattr(item, "text", str(item)).strip()
                if raw_text:
                    return self._align_and_deduplicate(raw_text, is_silence_at_end)
        except Exception as e:
            print(f"[ASR Error] {e}")
            return ""

        return ""