#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/CachyOS-Helper"
XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
INSTALL_DIR="$XDG_DATA_HOME/cachy-helper"
APPS_DIR="$XDG_DATA_HOME/applications"
ICON_DIR="$XDG_DATA_HOME/icons/hicolor/scalable/apps"
BIN_DIR="$HOME/.local/bin"
DESKTOP_TEMPLATE="$SCRIPT_DIR/cachy-helper.desktop.in"
DESKTOP_FILE="$APPS_DIR/cachy-helper.desktop"
LAUNCHER_FILE="$BIN_DIR/cachy-helper"
ICON_FILE="$ICON_DIR/cachy-helper.svg"

mkdir -p "$INSTALL_DIR" "$APPS_DIR" "$ICON_DIR" "$BIN_DIR"
rm -rf "$INSTALL_DIR"
cp -a "$SOURCE_DIR"/. "$INSTALL_DIR"

if command -v pacman >/dev/null 2>&1; then
  echo "Installing recommended runtime packages for CachyOS..."
  sudo pacman -S --needed python tk xdg-utils inetutils bind pacman-contrib
fi

cat >"$LAUNCHER_FILE" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec python "$INSTALL_DIR/app.py"
EOF
chmod +x "$LAUNCHER_FILE"

sed "s|__BINPATH__|$LAUNCHER_FILE|g" "$DESKTOP_TEMPLATE" >"$DESKTOP_FILE"
cp "$INSTALL_DIR/assets/cachy-helper.svg" "$ICON_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
fi

echo
echo "Installed successfully."
echo "Launcher: $LAUNCHER_FILE"
echo "Desktop file: $DESKTOP_FILE"
echo "Application data: $INSTALL_DIR"
echo
echo "You can now start the app with:"
echo "  cachy-helper"
