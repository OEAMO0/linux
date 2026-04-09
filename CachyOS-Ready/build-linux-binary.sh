#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/CachyOS-Helper"
ENTRYPOINT="$APP_DIR/app.py"
DIST_DIR="$SCRIPT_DIR/Linux-Build"
VENV_DIR="$SCRIPT_DIR/.build-venv"
WORK_DIR="$SCRIPT_DIR/.pyinstaller-build"
SPEC_DIR="$SCRIPT_DIR/.pyinstaller-spec"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This build script must be run on Linux."
  exit 1
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python was not found. Install it first."
  exit 1
fi

if ! "$PYTHON_BIN" -c "import tkinter" >/dev/null 2>&1; then
  echo "Tkinter is missing. On CachyOS run:"
  echo "  sudo pacman -S --needed python tk"
  exit 1
fi

rm -rf "$DIST_DIR" "$WORK_DIR" "$SPEC_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip wheel
python -m pip install -r "$SCRIPT_DIR/requirements-build.txt"

pyinstaller \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --name cachy-helper \
  --paths "$APP_DIR" \
  --distpath "$DIST_DIR" \
  --workpath "$WORK_DIR" \
  --specpath "$SPEC_DIR" \
  --add-data "$APP_DIR/assets/cachy-helper.svg:assets" \
  "$ENTRYPOINT"

chmod +x "$DIST_DIR/cachy-helper"

echo
echo "Linux executable created:"
echo "  $DIST_DIR/cachy-helper"
echo
echo "You can run it directly with:"
echo "  $DIST_DIR/cachy-helper"
