import threading
import queue
import time
import warnings
import numpy as np

# Suppress harmless WASAPI silence/discontinuity warnings
try:
    import soundcard as sc
    warnings.filterwarnings("ignore", category=sc.SoundcardRuntimeWarning)
except ImportError:
    pass

class LoopbackCapture:
    """
    Captures system audio playback via Windows WASAPI Loopback
    and dispatches audio slices asynchronously to prevent buffer dropouts.
    """
    def __init__(self, target_sample_rate: int = 16000, chunk_duration_sec: float = 0.5):
        self.sample_rate = target_sample_rate
        self.chunk_duration = chunk_duration_sec
        self.is_running = False
        self.audio_queue = queue.Queue(maxsize=50)
        self._capture_thread = None
        self._dispatch_thread = None
        self.callback = None

    def start(self, on_audio_chunk_callback):
        self.callback = on_audio_chunk_callback
        self.is_running = True

        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()

        self._dispatch_thread = threading.Thread(target=self._dispatch_loop, daemon=True)
        self._dispatch_thread.start()

        print("[Loopback] Desktop audio capture started.")

    def stop(self):
        self.is_running = False
        print("[Loopback] Desktop audio capture stopped.")

    def _capture_loop(self):
        try:
            import soundcard as sc
            speaker = sc.default_speaker()
            print(f"[Loopback] Active Speaker Endpoint: {speaker.name}")
            mic = sc.get_microphone(id=speaker.id, include_loopback=True)
            print(f"[Loopback] Capturing loopback on: {mic.name}")

            frames_per_chunk = int(self.sample_rate * self.chunk_duration)

            with mic.recorder(samplerate=self.sample_rate, channels=1) as recorder:
                while self.is_running:
                    try:
                        data = recorder.record(numframes=frames_per_chunk)
                        flattened = data[:, 0].astype(np.float32)
                        if not self.audio_queue.full():
                            self.audio_queue.put_nowait(flattened)
                    except Exception:
                        time.sleep(0.01)
        except Exception as e:
            print(f"[Loopback] Device error: {e}")
            while self.is_running:
                time.sleep(0.5)

    def _dispatch_loop(self):
        while self.is_running:
            try:
                chunk = self.audio_queue.get(timeout=0.1)
                if self.callback:
                    self.callback(chunk)
                self.audio_queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                time.sleep(0.01)