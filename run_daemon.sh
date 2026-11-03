#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

PYTHON_EXE="$SCRIPT_DIR/.venv/bin/python"

# Check if .venv exists
if [ ! -f "$PYTHON_EXE" ]; then
    # Try GUI popup if zenity or kdialog is installed, otherwise prompt in a spawned terminal
    if command -v zenity &>/dev/null; then
        if zenity --question --title="Setup Required" --text="The virtual environment was not found.\n\nRun the Linux installation setup now?" --width=350; then
            bash "$SCRIPT_DIR/scripts/install_linux.sh"
        else
            exit 1
        fi
    else
        echo "[!] .venv not found. Running installer..."
        bash "$SCRIPT_DIR/scripts/install_linux.sh"
    fi
fi

# Verify installation succeeded before detaching
if [ -f "$PYTHON_EXE" ]; then
    nohup "$PYTHON_EXE" "$SCRIPT_DIR/daemon/server.py" >/dev/null 2>&1 &
    echo "Live Captions Server running in background (PID: $!)."
else
    echo "Failed to start: environment setup incomplete."
    exit 1
fi