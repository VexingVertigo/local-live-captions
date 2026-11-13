param(
    [ValidateSet("auto", "lite", "balanced", "stream", "all")]
    [string]$Tier = "balanced"
)

Write-Host "=== Local Live Captions: Windows Compatibility & Setup ===" -ForegroundColor Cyan

# 1. Python Architecture & Version Check
$pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.10 or 3.11 (64-bit)."
    exit 1
}

$is64Bit = python -c "import struct; print(struct.calcsize('P') * 8)"
if ($is64Bit -ne "64") {
    Write-Error "Detected 32-bit Python. A 64-bit Python installation is strictly required."
    exit 1
}
Write-Host "[+] Python Version: $pythonVersion (64-bit)" -ForegroundColor Green

# 2. Hardware & VRAM Detection
$gpuInfo = Get-CimInstance Win32_VideoController | Where-Object { $_.Name -match "NVIDIA" } | Select-Object -First 1
$vramGB = 0

if ($gpuInfo) {
    $gpuName = $gpuInfo.Name
    # Query exact VRAM via nvidia-smi if available
    $smiVram = nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>$null | Select-Object -First 1
    if ($smiVram) {
        $vramGB = [math]::Round(([double]$smiVram / 1024), 1)
    } else {
        $vramGB = [math]::Round(([double]$gpuInfo.AdapterRAM / 1GB), 1)
    }
    Write-Host "[+] NVIDIA GPU Detected: $gpuName ($vramGB GB VRAM)" -ForegroundColor Green
    $deviceMode = "cuda"
} else {
    Write-Host "[!] No NVIDIA GPU detected. Defaulting to CPU mode." -ForegroundColor Yellow
    $deviceMode = "cpu"
}

if ($Tier -eq "auto") {
    if ($deviceMode -eq "cpu" -or $vramGB -lt 4) {
        $Tier = "lite"
    } elseif ($vramGB -lt 10) {
        $Tier = "balanced"
    } else {
        $Tier = "stream"
    }
    Write-Host "[+] Auto-selected tier based on hardware: $Tier" -ForegroundColor Cyan
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

# 4. Install Core & Tier Dependencies
Write-Host "[*] Upgrading pip and core build tools..."
& $pip install --upgrade pip setuptools wheel --quiet

Write-Host "[*] Installing PyTorch with CUDA 12 support..."
& $pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --quiet

Write-Host "[*] Installing base WebSocket, Audio, and Faster-Whisper stack..."
& $pip install faster-whisper websockets soundcard numpy pystray Pillow --quiet

if ($deviceMode -eq "cuda") {
    Write-Host "[*] Installing CTranslate2 CUDA 12 runtime binaries..."
    & $pip install nvidia-cublas-cu12 nvidia-cudnn-cu12 --quiet
}

if ($Tier -eq "lite" -or $Tier -eq "all") {
    Write-Host "[*] Installing Lite Tier (onnx-asr Parakeet TDT)..." -ForegroundColor Cyan
    if ($deviceMode -eq "cuda") {
        & $pip install "onnx-asr[cuda,hub]" --quiet
    } else {
        & $pip install "onnx-asr[cpu,hub]" --quiet
    }
}

if ($Tier -eq "stream" -or $Tier -eq "all") {
    Write-Host "[*] Installing Stream Tier (Kyutai STT / Moshi)..." -ForegroundColor Cyan
    & $pip install moshi huggingface-hub --quiet
}

# 5. Sanity Check
Write-Host "[*] Verifying runtime hardware profile..."
& $python -c "import sys; sys.path.insert(0, 'daemon'); from engine import detect_hardware_profile; print(detect_hardware_profile())"

Write-Host "`n[+] Setup complete for tier '$Tier'! Launch with: .\.venv\Scripts\python.exe daemon\server.py --tier $Tier" -ForegroundColor Green