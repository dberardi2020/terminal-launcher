#!/usr/bin/env bash
# Build the macOS .app and install it to /Applications, then clean up.
#
# py2app writes the bundle to ./dist, and leaving it there means a *second*
# "Terminal Launcher" shows up in Spotlight (the throwaway build copy next to the
# real one in /Applications). This script builds, installs, and removes build/
# and dist/ so exactly one copy — the installed one — exists when it finishes.
#
# Usage:  ./packaging/install-macos.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

APP="Terminal Launcher.app"
DEST="/Applications/$APP"
PY="${PYTHON:-.venv/bin/python}"

if [[ ! -x "$PY" ]]; then
  echo "error: no Python at '$PY'. Create the venv first (see packaging/README.md)," >&2
  echo "       or point PYTHON at your interpreter: PYTHON=python3 $0" >&2
  exit 1
fi

echo "==> Building $APP with py2app"
rm -rf build dist
"$PY" setup_py2app.py py2app >/dev/null

echo "==> Installing to $DEST"
rm -rf "$DEST"
cp -R "dist/$APP" "/Applications/"

echo "==> Cleaning build artifacts (so no duplicate lingers in Spotlight)"
rm -rf build dist

VER="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$DEST/Contents/Info.plist" 2>/dev/null || echo '?')"
echo "==> Installed Terminal Launcher $VER to /Applications"
echo "    (If the Dock still shows an old icon, remove and re-add the app to the Dock.)"
