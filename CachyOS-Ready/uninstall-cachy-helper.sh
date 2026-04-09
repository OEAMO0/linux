#!/usr/bin/env bash
set -euo pipefail

XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
INSTALL_DIR="$XDG_DATA_HOME/cachy-helper"
APPS_DIR="$XDG_DATA_HOME/applications"
ICON_DIR="$XDG_DATA_HOME/icons/hicolor/scalable/apps"
BIN_DIR="$HOME/.local/bin"

rm -rf "$INSTALL_DIR"
rm -f "$APPS_DIR/cachy-helper.desktop"
rm -f "$ICON_DIR/cachy-helper.svg"
rm -f "$BIN_DIR/cachy-helper"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
fi

echo "CachyOS Control Center was removed from the current user profile."
