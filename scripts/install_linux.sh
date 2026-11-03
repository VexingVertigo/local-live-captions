#!/usr/bin/env bash
set -e

echo "============================================================"
echo " Local Live Captions: Linux Installer & Environment Setup "
echo "============================================================"

# 1. Verify Hardware & Drivers
if command -v nvidia-smi &> /dev/null; then
    echo "[OK] NVIDIA GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    DEVICE_MODE="cuda"
else
    echo "[WARN] 'nvidia-smi' not found. Will default to CPU (int8) mode."
    DEVICE_MODE="cpu"
fi

# 2. Check Python 3.10+
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed. Please install python3 and python3-venv."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "[OK] Using Python $PYTHON_VERSION"

# 3. Create Virtual Environment
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -d ".venv" ]; then
    echo "[+] Creating virtual environment at .venv..."
    python3 -m venv .venv
else
    echo "[OK] Virtual environment already exists."
fi

source .venv/bin/activate
pip install --upgrade pip setuptools wheel --quiet

# 4. Install PyTorch & Faster-Whisper
echo "[+] Installing PyTorch with CUDA 12 support..."
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124 --quiet

echo "[+] Installing Faster-Whisper, WebSockets, and Audio stack..."
pip install faster-whisper websockets sounddevice numpy pynvml --quiet

# 5. Install CUDA 12 Shared Libraries for CTranslate2
if [ "$DEVICE_MODE" = "cuda" ]; then
    echo "[+] Installing CUDA 12 runtime libraries (cuBLAS, cuDNN)..."
    pip install nvidia-cublas-cu12 nvidia-cudnn-cu12 --quiet
fi

# 6. Sanity Check
echo "[+] Verifying faster-whisper runtime..."
python3 -c "
import ctranslate2
devs = ctranslate2.get_cuda_device_count()
print(f'CTranslate2 CUDA Devices: {devs}')
from faster_whisper import WhisperModel
print('faster-whisper verification: OK')
"

echo ""
echo "============================================================"
echo " Setup complete! "
echo " To start the server with terminal output: "
echo "   ./run_daemon_debug.sh"
echo " To start silently in background: "
echo "   ./run_daemon.sh"
echo "============================================================"