Write-Host "=== Local Live Captions: Windows Compatibility & Setup ===" -ForegroundColor Cyan

# 1. Python Architecture & Version Check
$pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.10 or 3.11 (64-bit)."
    exit 1
}

$is64Bit = python -c "import struct; print(struct.calcsize('P') * 8)"
if ($is64Bit -ne "64") {
    Write-Error "Detected 32-bit Python. A 64-bit Python installation is strictly required for CUDA and CTranslate2."
    exit 1
}
Write-Host "[+] Python Version: $pythonVersion (64-bit)" -ForegroundColor Green

# 2. Hardware Detection (GPU vs CPU)
$gpuName = Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name | Where-Object { $_ -match "NVIDIA" } | Select-Object -First 1

if ($gpuName) {
    Write-Host "[+] Supported NVIDIA GPU Detected: $gpuName" -ForegroundColor Green
    $deviceMode = "cuda"
} else {
    Write-Host "[!] No NVIDIA GPU detected. Engine will default to CPU (int8) mode." -ForegroundColor Yellow
    $deviceMode = "cpu"
}

# 3. Virtual Environment Creation
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Test-Path ".venv")) {
    Write-Host "[*] Creating virtual environment (.venv)..."
    python -m venv .venv
}

$pip = ".\.venv\Scripts\pip.exe"
$python = ".\.venv\Scripts\python.exe"

# 4. Install Dependencies
Write-Host "[*] Upgrading pip and core build tools..."
& $pip install --upgrade pip setuptools wheel --quiet

Write-Host "[*] Installing PyTorch with CUDA 12 support..."
& $pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --quiet

Write-Host "[*] Installing Faster-Whisper, WebSockets, and Audio Capture..."
& $pip install faster-whisper websockets soundcard numpy pystray Pillow --quiet

if ($deviceMode -eq "cuda") {
    Write-Host "[*] Installing CTranslate2 CUDA 12 runtime binaries..."
    & $pip install nvidia-cublas-cu12 nvidia-cudnn-cu12 --quiet
}

# 5. Sanity Check
Write-Host "[*] Verifying runtime inference..."
$verifyScript = @"
import ctranslate2
import torch
from faster_whisper import WhisperModel

gpu_available = torch.cuda.is_available()
c2_devices = ctranslate2.get_cuda_device_count()
print(f'PyTorch CUDA Accessible: {gpu_available}')
print(f'CTranslate2 CUDA Devices: {c2_devices}')
if gpu_available:
    print(f'Active Device: {torch.cuda.get_device_name(0)}')
"@

& $python -c $verifyScript

Write-Host "`n[+] Setup complete! Double-click run_daemon.vbs (silent) or run_daemon_debug.vbs (console) to launch." -ForegroundColor Green