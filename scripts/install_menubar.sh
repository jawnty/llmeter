#!/bin/bash
# Install the llmeter menu bar app.
#
# Creates a menu bar runtime venv, registers a launchd LaunchAgent so it starts
# at login, and launches it now.
#
# Idempotent: re-running replaces any prior bundle + LaunchAgent cleanly.
# Requires no user-granted permissions (no osascript / Login Item / System
# Events automation).

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
LOG_DIR="${LLMETER_LOG_DIR:-$HOME/.llmeter/logs}"
PLIST="$HOME/Library/LaunchAgents/com.llmeter.menubar.plist"
DOMAIN="gui/$(id -u)"
LABEL="com.llmeter.menubar"

echo "[llmeter] installing menu bar"
echo "[llmeter] menubar venv: $MENUBAR_VENV"

# 1. venv
if [ ! -d "$MENUBAR_VENV" ]; then
  "$PYTHON" -m venv "$MENUBAR_VENV"
fi
# shellcheck disable=SC1091
. "$MENUBAR_VENV/bin/activate"
python -m pip install --upgrade pip >/dev/null
echo "[llmeter] installing menu bar deps (rumps + llmeter runtime)..."
pip install -q -r requirements.txt
pip install -q -r requirements-menubar.txt

# 2. remove any older py2app bundle/processes from previous test builds.
osascript -e 'tell application "Llmeter" to quit' >/dev/null 2>&1 || true
pkill -f "/Applications/Llmeter.app" >/dev/null 2>&1 || true
pkill -x "Llmeter" >/dev/null 2>&1 || true
pkill -f "llmeter.menubar" >/dev/null 2>&1 || true
rm -rf "$APP_DEST"

# 3. LaunchAgent — runs the menu bar module from the installed venv.
mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$MENUBAR_VENV/bin/python</string>
    <string>-m</string>
    <string>llmeter.menubar</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$DIR</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <false/>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/menubar.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/menubar.log</string>
</dict>
</plist>
PLIST

# 4. (re)load the LaunchAgent and kick it now.
launchctl bootout "$DOMAIN" "$PLIST" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$PLIST"
launchctl kickstart -k "$DOMAIN/$LABEL" >/dev/null 2>&1 || true

echo "[llmeter] menu bar installed and registered to start at login"
