#!/usr/bin/env bash
set -e

TIER="balanced"
for arg in "$@"; do
    case $arg in
        --tier=*) TIER="${arg#*=}" ;;
        --lite) TIER="lite" ;;
        --stream) TIER="stream" ;;
        --auto) TIER="auto" ;;
        --all) TIER="all" ;;
    esac
done

echo "============================================================"
echo " Local Live Captions: Linux Installer & Environment Setup "
echo "============================================================"

# 1. Verify Hardware & VRAM
VRAM_GB=0
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1)
    VRAM_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n 1)
    VRAM_GB=$(python3 -c "print(round(${VRAM_MB} / 1024, 1))")
    echo "[OK] NVIDIA GPU detected: $GPU_NAME (${VRAM_GB} GB VRAM)"
    DEVICE_MODE="cuda"
else
    echo "[WARN] 'nvidia-smi' not found. Defaulting to CPU mode."
    DEVICE_MODE="cpu"
fi

if [ "$TIER" = "auto" ]; then
    TIER=$(python3 -c "
v = float('${VRAM_GB}')
if '${DEVICE_MODE}' == 'cpu' or v < 4.0: print('lite')
elif v < 10.0: print('balanced')
else: print('stream')
")
    echo "[OK] Auto-selected tier based on hardware: $TIER"
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

# 4. Install Core & Tier Dependencies
echo "[+] Installing PyTorch with CUDA 12 support..."
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124 --quiet

echo "[+] Installing base Faster-Whisper, WebSockets, and Audio stack..."
pip install faster-whisper websockets soundcard numpy pynvml --quiet

if [ "$DEVICE_MODE" = "cuda" ]; then
    echo "[+] Installing CUDA 12 runtime libraries (cuBLAS, cuDNN)..."
    pip install nvidia-cublas-cu12 nvidia-cudnn-cu12 --quiet
fi

if [ "$TIER" = "lite" ] || [ "$TIER" = "all" ]; then
    echo "[+] Installing Lite Tier (onnx-asr Parakeet TDT)..."
    if [ "$DEVICE_MODE" = "cuda" ]; then
        pip install "onnx-asr[cuda,hub]" --quiet
    else
        pip install "onnx-asr[cpu,hub]" --quiet
    fi
fi

if [ "$TIER" = "stream" ] || [ "$TIER" = "all" ]; then
    echo "[+] Installing Stream Tier (Kyutai STT / Moshi)..."
    pip install moshi huggingface-hub --quiet
fi

# 5. Sanity Check
echo "[+] Verifying runtime hardware profile..."
python3 -c "import sys; sys.path.insert(0, 'daemon'); from engine import detect_hardware_profile; print(detect_hardware_profile())"

echo ""
echo "============================================================"
echo " Setup complete (tier: $TIER)!"
echo " Launch command: .venv/bin/python daemon/server.py --tier $TIER"
echo "============================================================"