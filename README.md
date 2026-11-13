### Initial Release (Local Live Captions)

Local Live Captions is a self-hosted, real-time AI closed-captioning engine and browser overlay powered by `faster-whisper` and CTranslate2 with NVIDIA CUDA acceleration.

---

### Downloads
* **Source Code:** Download `Source code (zip)` or `Source code (tar.gz)` below, or clone the repository directly.
* **Browser Extension:** Load the unpacked `clients/extension/` directory in Chrome, Edge, Brave, or Firefox.

---

### Key Features
* **GPU-Accelerated Streaming ASR:** Runs `large-v3-turbo` in `float16` via CTranslate2 CUDA 12, with automatic CPU `INT8` fallback.
* **VAD Clause Gating & Anti-Repetition:** Cleans up partial hypotheses and suppresses Whisper silence hallucinations in real time.
* **Multi-Speaker Diarization:** Integrates NeMo (`ecapa_tdnn`) speaker embeddings to color-code distinct speakers on screen.
* **Universal Browser Video Overlay:** Tracks active HTML5 `<video>` elements (including fullscreen and YouTube client-side navigation) with customizable colors, background opacity, and an `Alt + C` quick toggle.
* **Dual Audio Ingestion Modes:** Captures local desktop soundcard loopback automatically, or accepts raw 16kHz PCM audio streams over WebSockets (`ws://0.0.0.0:8765`) from remote clients like Android TV.

---

### Setup & Project Structure
```text
local-live-captions/
├── daemon/                 <-- WebSocket ASR & speaker diarization server
├── clients/
│   └── extension/          <-- Manifest V3 browser overlay extension
├── scripts/                <-- Automated Windows & Linux environment installers
├── run_daemon.vbs          <-- Silent Windows background launcher
└── run_daemon.sh           <-- Linux launcher
```

**Quick Start:**
1. Run `scripts/install_windows.ps1` (Windows) or `scripts/install_linux.sh` (Linux) to set up the virtual environment and CUDA dependencies.
2. Start the server via `run_daemon.vbs` (local desktop capture) or `.venv/bin/python daemon/server.py --no-loopback` (dedicated remote compute node).
3. Load `clients/extension/` in your browser and connect to `127.0.0.1:8765` (or your host machine's LAN IP).

### Browser Extension Setup

1. Download and extract the latest release archive (or clone this repository).
2. Open your browser's extensions page:
   * **Chrome:** `chrome://extensions`
   * **Edge:** `edge://extensions`
   * **Brave:** `brave://extensions`
3. Enable **Developer mode** using the toggle in the top-right corner.
4. Click **Load unpacked** and select the `clients/extension` folder from this repository.
5. Click the extension icon in your toolbar to verify the connection to `127.0.0.1:8765` (or enter your host machine's LAN IP) and customize caption appearance.

> **Tip:** Press `Alt + C` on any webpage to quickly toggle the live caption overlay on or off.
---

### Edge Cases & Notes
* **Headless / Remote Compute Node (`--no-loopback`):** When offloading transcription from an external device (such as an Android TV box) to a Linux machine without local audio capture, pass `--no-loopback` so the daemon skips soundcard initialization.
* **Firewall Access:** If connecting from another device on your LAN, allow incoming TCP traffic on port `8765` (`sudo ufw allow 8765/tcp` on Linux or Windows Defender Firewall).

---

### Tested Environment
* **Desktop Host:** Windows 11, AMD Ryzen 7 5800X, NVIDIA GeForce RTX 5080 (CUDA 12)
* **Linux Compute Node:** Ubuntu Linux (Lenovo Legion 5) streaming to Google TV Streamer (4K)
* **Verified:** YouTube, live streams, and local media playback with multi-speaker color separation

---

### Support & Feedback
Found this build useful?
* **Support the project:** [![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20the%20Project-F16061?style=flat-square&logo=ko-fi&logoColor=white)](https://ko-fi.com/vexingvertigo)
* **Report issues:** Submit feedback via the repository [Issues tab](https://github.com/VexingVertigo/local-live-captions/issues) with your OS, GPU/CUDA version, and terminal logs.
