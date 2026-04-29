#!/bin/bash
set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

HOST="${TOKMON_HOST:-127.0.0.1}"
PORT="${TOKMON_PORT:-4001}"
LOG_DIR="${TOKMON_LOG_DIR:-$HOME/.openclaw/logs}"
PLIST="$HOME/Library/LaunchAgents/com.tokmon.monitor.plist"
DOMAIN="gui/$(id -u)"

echo "[tokmon] setting up virtualenv at $DIR/.venv"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
pip install -r requirements.txt

mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.tokmon.monitor</string>
  <key>ProgramArguments</key>
  <array>
    <string>$DIR/.venv/bin/python</string>
    <string>-m</string>
    <string>tokmon</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$DIR</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PYTHONUNBUFFERED</key>
    <string>1</string>
    <key>TOKMON_HOST</key>
    <string>$HOST</string>
    <key>TOKMON_PORT</key>
    <string>$PORT</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/tokmon.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/tokmon.log</string>
</dict>
</plist>
PLIST

launchctl bootout "$DOMAIN" "$PLIST" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$PLIST"
launchctl kickstart -k "$DOMAIN/com.tokmon.monitor" 2>/dev/null || true

echo
echo "[tokmon] installed and running."
echo "[tokmon] open http://$HOST:$PORT"
echo "[tokmon] logs: $LOG_DIR/tokmon.log"
