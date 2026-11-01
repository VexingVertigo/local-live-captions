#!/usr/bin/env bash
set -e

echo "============================================================"
echo " Local Live Captions: Linux Installer & Environment Setup "
echo "============================================================"

# 1. Verify NVIDIA Driver & CUDA
if ! command -v nvidia-smi &> /dev/null; then
    echo "[ERROR] 'nvidia-smi' not found. Please install NVIDIA proprietary drivers."
    exit 1
fi

echo "[OK] NVIDIA GPU detected:"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

# 2. Check for Python 3.10+
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
pip install --upgrade pip setuptools wheel

# 4. Install CUDA-enabled PyTorch & Audio Stack
echo "[+] Installing PyTorch with CUDA support..."
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124

echo "[+] Installing audio capture, WebSocket, and NVIDIA monitoring dependencies..."
pip install websockets soundcard numpy pynvml

# 5. Install NeMo streaming toolkit
echo "[+] Installing NVIDIA NeMo ASR tools..."
pip install "nemo_toolkit[asr]" || echo "[!] Notice: If NeMo build fails from wheel, ensure libsndfile1-dev and ffmpeg are installed via apt."

echo ""
echo "============================================================"
echo " Setup complete! "
echo " To start the local daemon, run: "
echo "   source .venv/bin/activate"
echo "   python daemon/server.py"
echo "============================================================"