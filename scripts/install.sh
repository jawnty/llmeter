#!/bin/bash
set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

HOST="${LLMETER_HOST:-127.0.0.1}"
PORT="${LLMETER_PORT:-4001}"
LOG_DIR="${LLMETER_LOG_DIR:-$HOME/.llmeter/logs}"
PLIST="$HOME/Library/LaunchAgents/com.llmeter.monitor.plist"
DOMAIN="gui/$(id -u)"
PYTHON="${LLMETER_PYTHON:-python3}"

echo "[llmeter] setting up virtualenv at $DIR/.venv"
"$PYTHON" -m venv .venv
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
  <string>com.llmeter.monitor</string>
  <key>ProgramArguments</key>
  <array>
    <string>$DIR/.venv/bin/python</string>
    <string>-m</string>
    <string>llmeter</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$DIR</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PYTHONUNBUFFERED</key>
    <string>1</string>
    <key>LLMETER_HOST</key>
    <string>$HOST</string>
    <key>LLMETER_PORT</key>
    <string>$PORT</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/llmeter.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/llmeter.log</string>
</dict>
</plist>
PLIST

launchctl bootout "$DOMAIN" "$PLIST" 2>/dev/null || true
if command -v lsof >/dev/null 2>&1; then
  while read -r PID; do
    [ -z "$PID" ] && continue
    if ps -p "$PID" -o command= | grep -q -- "-m llmeter"; then
      kill "$PID" 2>/dev/null || true
    fi
  done < <(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)
fi
launchctl bootstrap "$DOMAIN" "$PLIST"
launchctl kickstart -k "$DOMAIN/com.llmeter.monitor" 2>/dev/null || true

echo
echo "[llmeter] installed and running."
echo "[llmeter] open http://$HOST:$PORT"
echo "[llmeter] logs: $LOG_DIR/llmeter.log"
