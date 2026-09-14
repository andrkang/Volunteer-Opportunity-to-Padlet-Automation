#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Harvest Opportunities"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
DMG_STAGING_DIR="$(mktemp -d "${TMPDIR:-/tmp}/harvest-opportunities-dmg.XXXXXX")"

cleanup() {
  rm -rf "$DMG_STAGING_DIR"
}
trap cleanup EXIT

cd "$ROOT_DIR"

if ! "$PYTHON_BIN" -m PyInstaller --version >/dev/null 2>&1; then
  echo "PyInstaller is not installed for $PYTHON_BIN."
  echo "Install it with: $PYTHON_BIN -m pip install -r requirements-packaging.txt"
  exit 1
fi

rm -rf build "dist/$APP_NAME.app" "dist/$APP_NAME" "dist/$APP_NAME-macOS.dmg" "dist/dmg-root"
export PYINSTALLER_CONFIG_DIR="$ROOT_DIR/build/pyinstaller-config"
mkdir -p "$PYINSTALLER_CONFIG_DIR"

"$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --windowed \
  --name "$APP_NAME" \
  --icon "generated_assets/app-icon.icns" \
  --add-data "generated_assets:generated_assets" \
  main.py

# Stage outside cloud-synced folders so Finder/file-provider metadata is not
# embedded in the disk image and invalidating strict code-signature checks.
ditto --norsrc --noextattr "dist/$APP_NAME.app" "$DMG_STAGING_DIR/$APP_NAME.app"
xattr -cr "$DMG_STAGING_DIR/$APP_NAME.app"
codesign --verify --deep --strict "$DMG_STAGING_DIR/$APP_NAME.app"
ln -s /Applications "$DMG_STAGING_DIR/Applications"

hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$DMG_STAGING_DIR" \
  -ov \
  -format UDZO \
  "dist/$APP_NAME-macOS.dmg"

echo "Built: dist/$APP_NAME.app"
echo "Built: dist/$APP_NAME-macOS.dmg"
