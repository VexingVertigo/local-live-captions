import threading
import time
import numpy as np

class LoopbackCapture:
    """
    Captures audio from the default speaker/headphone playback device
    (WASAPI Loopback on Windows, PulseAudio/PipeWire monitor on Linux).
    """
    def __init__(self, target_sample_rate: int = 16000, chunk_duration_sec: float = 0.5):
        self.sample_rate = target_sample_rate
        self.chunk_duration = chunk_duration_sec
        self.is_running = False
        self._thread = None
        self.callback = None

    def start(self, on_audio_chunk_callback):
        self.callback = on_audio_chunk_callback
        self.is_running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        print("[Loopback] Desktop audio capture started.")

    def stop(self):
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        print("[Loopback] Desktop audio capture stopped.")

    def _capture_loop(self):
        try:
            import soundcard as sc
            speaker = sc.default_speaker()
            mic = sc.get_microphone(id=speaker.id, include_loopback=True)
            frames_per_chunk = int(self.sample_rate * self.chunk_duration)

            with mic.recorder(samplerate=self.sample_rate, channels=1) as recorder:
                while self.is_running:
                    # Capture 16kHz mono audio slice
                    data = recorder.record(numframes=frames_per_chunk)
                    flattened = data[:, 0].astype(np.float32)
                    if self.callback:
                        self.callback(flattened)
        except Exception as e:
            print(f"[Loopback] Native loopback capture unavailable ({e}).")
            # Keep thread alive to avoid crashing if loopback driver is temporarily busy
            while self.is_running:
                time.sleep(0.5)