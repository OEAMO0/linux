#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/CachyOS-Helper"

if ! command -v python >/dev/null 2>&1; then
  echo "Python is required but was not found."
  exit 1
fi

if ! python -c "import tkinter" >/dev/null 2>&1; then
  echo "Tkinter is missing. On CachyOS run:"
  echo "  sudo pacman -S --needed python tk"
  exit 1
fi

exec python "$APP_DIR/app.py"
