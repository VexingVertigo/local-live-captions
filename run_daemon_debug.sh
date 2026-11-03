#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

PYTHON_EXE="$SCRIPT_DIR/.venv/bin/python"

# If .venv does not exist, run the setup script automatically
if [ ! -f "$PYTHON_EXE" ]; then
    echo "Virtual environment (.venv) not found."
    read -rp "Run Linux installation setup now? [Y/n]: " choice
    case "$choice" in 
        [yY][eE][sS]|[yY]|"") 
            bash "$SCRIPT_DIR/scripts/install_linux.sh"
            ;;
        *)
            echo "Cannot start server without dependencies installed."
            exit 1
            ;;
    esac
fi

if [ -t 0 ]; then
    echo "Starting Live Captions Server..."
    "$PYTHON_EXE" "$SCRIPT_DIR/daemon/server.py"
    echo -e "\nServer stopped."
    read -rp "Press Enter to exit..."
    exit 0
fi

TERMINALS=("x-terminal-emulator -e" "gnome-terminal --" "konsole -e" "xfce4-terminal -e" "alacritty -e" "kitty" "xterm -e")
for term in "${TERMINALS[@]}"; do
    bin=$(echo "$term" | awk '{print $1}')
    if command -v "$bin" &>/dev/null; then
        exec $term bash -c "bash '$SCRIPT_DIR/run_daemon_debug.sh'"
    fi
done