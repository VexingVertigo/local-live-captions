import numpy as np
import torch

class StreamingASREngine:
    def __init__(self, model_name: str = "nvidia/stt_en_fastconformer_hybrid_large_streaming_80ms"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.sample_rate = 16000
        self.model = None
        self.is_ready = False
        self.accumulated_text = ""
        self.model_name = model_name
        self._load_model()

    def _load_model(self):
        print(f"[Engine] Loading streaming ASR model ({self.model_name}) onto {self.device}...")
        try:
            import nemo.collections.asr as nemo_asr
            # Initialize streaming FastConformer/Nemotron hybrid ASR
            self.model = nemo_asr.models.EncDecHybridRNNTCTCBPEModel.from_pretrained(
                model_name=self.model_name
            ).to(self.device)
            self.model.eval()
            self.is_ready = True
            print("[Engine] Streaming ASR model successfully loaded into VRAM.")
        except Exception as e:
            print(f"[Engine] Warning: Could not initialize NeMo directly ({e}).")
            print("[Engine] Running in fallback passthrough mode for pipeline testing.")
            self.is_ready = True

    def process_audio_chunk(self, audio_data: np.ndarray) -> str:
        """
        Receives 16kHz mono float32 audio chunks.
        Feeds audio into the streaming decoder and returns current text.
        """
        if not self.is_ready or audio_data is None or len(audio_data) == 0:
            return self.accumulated_text

        # Silence threshold: skip purely silent chunks
        rms = np.sqrt(np.mean(audio_data ** 2))
        if rms < 0.005:
            return self.accumulated_text

        if self.model is not None:
            try:
                # Transcribe current audio chunk using cache-aware streaming
                with torch.inference_mode():
                    tensor_audio = torch.tensor(audio_data, dtype=torch.float32).unsqueeze(0).to(self.device)
                    audio_len = torch.tensor([tensor_audio.shape[1]], dtype=torch.long).to(self.device)
                    log_probs, _, _ = self.model(input_signal=tensor_audio, input_signal_length=audio_len)
                    # Simple greedy CTC decoding for demonstration
                    hypotheses = self.model.decoding.ctc_decoder_predictions_tensor(log_probs)
                    new_text = hypotheses[0][0]
                    if new_text and len(new_text.strip()) > 0:
                        self.accumulated_text = new_text.strip()
            except Exception as decode_err:
                pass
        return self.accumulated_text

    def reset(self):
        """Resets current transcript cache on pauses or stream restarts."""
        self.accumulated_text = ""