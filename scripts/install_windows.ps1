# Local Live Captions: Windows Automated Setup Script
$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Local Live Captions: Windows Setup & CUDA Environment " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Check for NVIDIA GPU
try {
    $gpu = Get-CimInstance Win32_VideoController | Where-Object { $_.Name -like "*NVIDIA*" } | Select-Object -First 1
    if (-not $gpu) {
        Write-Warning "No NVIDIA GPU detected in Windows Management Instrumentation."
    } else {
        Write-Host "[OK] GPU Detected: $($gpu.Name)" -ForegroundColor Green
    }
} catch {
    Write-Host "[!] Could not query GPU info via WMI, continuing..." -ForegroundColor Yellow
}

# 2. Check Python installation
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.10+ from python.org."
    exit 1
}

$pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "[OK] Found Python $pyVer" -ForegroundColor Green

# 3. Create and activate .venv
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Test-Path ".venv")) {
    Write-Host "[+] Creating virtual environment in .venv..." -ForegroundColor Yellow
    python -m venv .venv
} else {
    Write-Host "[OK] Virtual environment exists." -ForegroundColor Green
}

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$venvPip = Join-Path $repoRoot ".venv\Scripts\pip.exe"

# Upgrade pip
& $venvPython -m pip install --upgrade pip setuptools wheel

# 4. Install PyTorch with CUDA 12.4
Write-Host "[+] Installing PyTorch with CUDA acceleration..." -ForegroundColor Yellow
& $venvPip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124

# 5. Install Audio Loopback (WASAPI), WebSockets, and NVML
Write-Host "[+] Installing WASAPI loopback, websockets, and pynvml..." -ForegroundColor Yellow
& $venvPip install websockets soundcard numpy pynvml

# 6. Install NeMo ASR tools
Write-Host "[+] Installing NVIDIA NeMo ASR components..." -ForegroundColor Yellow
try {
    & $venvPip install "nemo_toolkit[asr]"
} catch {
    Write-Warning "NeMo direct wheel build encountered an issue. The daemon fallback mode will operate."
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " Installation Successful!" -ForegroundColor Green
Write-Host " To start the backend server, run:" -ForegroundColor Cyan
Write-Host "   .\.venv\Scripts\activate" -ForegroundColor White
Write-Host "   python daemon\server.py" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Green