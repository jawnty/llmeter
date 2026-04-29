#!/bin/bash
# Install the llmeter menu bar app.
#
# Builds Llmeter.app with py2app in alias mode (fast, references the source
# under ~/.llmeter/app), copies it to /Applications, registers it as a Login
# Item, and launches it.
#
# Idempotent: re-running removes any prior bundle + Login Item before
# installing the new one. Safe to run after every dashboard install.

set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "[llmeter] menu bar app is macOS-only; skipping" >&2
  exit 0
fi

PYTHON="${LLMETER_PYTHON:-python3}"
MENUBAR_VENV="$HOME/.llmeter/menubar-venv"
APP_DEST="/Applications/Llmeter.app"
APP_NAME="Llmeter"
LOGIN_ITEM_NAME="Llmeter"

echo "[llmeter] installing menu bar app"
echo "[llmeter] menubar venv: $MENUBAR_VENV"

# 1. venv
if [ ! -d "$MENUBAR_VENV" ]; then
  "$PYTHON" -m venv "$MENUBAR_VENV"
fi
# shellcheck disable=SC1091
. "$MENUBAR_VENV/bin/activate"
python -m pip install --upgrade pip >/dev/null
echo "[llmeter] installing menu bar deps (rumps, py2app, llmeter runtime)..."
pip install -q -r requirements.txt
pip install -q -r requirements-menubar.txt

# 2. build alias bundle (fast; references this source tree)
echo "[llmeter] building Llmeter.app (py2app alias mode)..."
rm -rf build dist
python setup_menubar.py py2app -A >/dev/null

if [ ! -d "dist/Llmeter.app" ]; then
  echo "[llmeter] py2app did not produce dist/Llmeter.app" >&2
  exit 1
fi

# 3. install to /Applications (idempotent)
# Try to quit any running instance first
osascript -e 'tell application "Llmeter" to quit' >/dev/null 2>&1 || true
pkill -f "/Applications/Llmeter.app" >/dev/null 2>&1 || true
rm -rf "$APP_DEST"
cp -R "dist/Llmeter.app" "$APP_DEST"

# 4. Login Item (idempotent: remove existing entry by name first)
osascript -e "tell application \"System Events\" to delete (every login item whose name is \"$LOGIN_ITEM_NAME\")" >/dev/null 2>&1 || true
LOGIN_OK=1
osascript -e "tell application \"System Events\" to make login item at end with properties {path:\"$APP_DEST\", hidden:false, name:\"$LOGIN_ITEM_NAME\"}" >/dev/null 2>&1 || LOGIN_OK=0

# 5. launch now
open -a "$APP_NAME" || true

if [ "$LOGIN_OK" = "1" ]; then
  echo "[llmeter] menu bar app installed at $APP_DEST and added to Login Items"
else
  echo "[llmeter] menu bar app installed at $APP_DEST"
  echo "[llmeter] could not register Login Item automatically. To start on login,"
  echo "[llmeter] grant Automation permission to your terminal for System Events,"
  echo "[llmeter] or add Llmeter.app via System Settings → General → Login Items."
fi
