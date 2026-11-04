# \# Local Live Captions

# 

# Real-time, local, private AI live captions for web video and desktop audio powered by `faster-whisper` and CTranslate2 with NVIDIA CUDA acceleration.

# 

# \## Features

# \- \*\*GPU-Accelerated Inference:\*\* Runs `large-v3-turbo` in float16 via CTranslate2 CUDA 12, with automatic CPU INT8 fallback.

# \- \*\*Agreement-Driven Streaming:\*\* Uses sliding audio chunking, Silero VAD gating, and prefix verification to prevent stuttering and subtitle jitter.

# \- \*\*Zero-Config Launchers:\*\* One-click silent (`.vbs` / `.sh`) and debug console launchers for Windows and Linux.

# \- \*\*System Tray Management:\*\* Minimal system tray icon showing real-time transcription status.

# \- \*\*Browser Extension:\*\* Manifest V3 extension with custom styling, background opacity controls, and speaker color-coding.

# 

# \## Prerequisites

# \- \*\*OS:\*\* Windows 10/11 (64-bit) or Linux (Ubuntu/Debian/Arch)

# \- \*\*Python:\*\* Python 3.10 or 3.11 (64-bit)

# \- \*\*Hardware:\*\* NVIDIA GPU with 4GB+ VRAM recommended (falls back to CPU if unavailable).

# 

# \## Installation

# 

# \### Windows

# Run PowerShell as Administrator or standard user:

# ```powershell

# powershell -ExecutionPolicy Bypass -File scripts\\install\_windows.ps1

