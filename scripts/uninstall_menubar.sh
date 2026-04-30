#!/bin/bash
# Uninstall the llmeter menu bar app: quit it, remove /Applications/Llmeter.app,
# unload + remove the launchd LaunchAgent, and remove the menubar venv.

set -euo pipefail

if [ "$(uname -s)" != "Darwin" ]; then
  echo "[llmeter] menu bar app is macOS-only; nothing to uninstall" >&2
  exit 0
fi

APP_DEST="/Applications/Llmeter.app"
MENUBAR_VENV="$HOME/.llmeter/menubar-venv"
PLIST="$HOME/Library/LaunchAgents/com.llmeter.menubar.plist"
DOMAIN="gui/$(id -u)"

osascript -e 'tell application "Llmeter" to quit' >/dev/null 2>&1 || true
pkill -f "/Applications/Llmeter.app" >/dev/null 2>&1 || true
pkill -x "Llmeter" >/dev/null 2>&1 || true
pkill -f "llmeter.menubar" >/dev/null 2>&1 || true

launchctl bootout "$DOMAIN" "$PLIST" 2>/dev/null || true
rm -f "$PLIST"

rm -rf "$APP_DEST"
rm -rf "$MENUBAR_VENV"

echo "[llmeter] menu bar app removed"
