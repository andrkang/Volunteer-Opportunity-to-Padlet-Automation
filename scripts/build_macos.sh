#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Harvest Opportunities"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

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

mkdir -p "dist/dmg-root"
cp -R "dist/$APP_NAME.app" "dist/dmg-root/"
ln -s /Applications "dist/dmg-root/Applications"

hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "dist/dmg-root" \
  -ov \
  -format UDZO \
  "dist/$APP_NAME-macOS.dmg"

echo "Built: dist/$APP_NAME.app"
echo "Built: dist/$APP_NAME-macOS.dmg"
