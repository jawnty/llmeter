#!/bin/bash
set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

echo "[tokmon] creating venv at $DIR/.venv"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
pip install -r requirements.txt

mkdir -p ~/.openclaw/logs

PLIST=~/Library/LaunchAgents/com.tokmon.monitor.plist
mkdir -p ~/Library/LaunchAgents
cp launchd/com.tokmon.monitor.plist "$PLIST"

# Reload
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo
echo "[tokmon] installed and running."
echo "[tokmon] open http://localhost:4001"
echo "[tokmon] logs: ~/.openclaw/logs/tokmon.log"
