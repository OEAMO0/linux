#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APPDIR="$SCRIPT_DIR/AppDir"
BINARY="$SCRIPT_DIR/Linux-Build/cachy-helper"
ICON_SOURCE="$SCRIPT_DIR/CachyOS-Helper/assets/cachy-helper.svg"
DESKTOP_SOURCE="$SCRIPT_DIR/cachy-helper.desktop.in"
DESKTOP_TARGET="$APPDIR/cachy-helper.desktop"
APPIMAGE_NAME="CachyOS-Control-Center-x86_64.AppImage"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This AppImage script must be run on Linux."
  exit 1
fi

"$SCRIPT_DIR/build-linux-binary.sh"

if ! command -v appimagetool >/dev/null 2>&1; then
  echo "appimagetool is required to build an AppImage."
  echo "Install it first, then rerun this script."
  echo "If you use yay, a common option is:"
  echo "  yay -S --needed appimagetool"
  exit 1
fi

rm -rf "$APPDIR" "$SCRIPT_DIR/$APPIMAGE_NAME"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/scalable/apps"

cp "$BINARY" "$APPDIR/usr/bin/cachy-helper"
cp "$ICON_SOURCE" "$APPDIR/usr/share/icons/hicolor/scalable/apps/cachy-helper.svg"
sed "s|__BINPATH__|cachy-helper|g" "$DESKTOP_SOURCE" >"$DESKTOP_TARGET"

cat >"$APPDIR/AppRun" <<'EOF'
#!/usr/bin/env bash
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$HERE/usr/bin/cachy-helper" "$@"
EOF
chmod +x "$APPDIR/AppRun"

cp "$DESKTOP_TARGET" "$APPDIR/"
cp "$ICON_SOURCE" "$APPDIR/cachy-helper.svg"
ln -sf "cachy-helper.svg" "$APPDIR/.DirIcon"

appimagetool "$APPDIR" "$SCRIPT_DIR/$APPIMAGE_NAME"

echo
echo "AppImage created:"
echo "  $SCRIPT_DIR/$APPIMAGE_NAME"
