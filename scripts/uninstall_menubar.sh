#!/bin/bash
# Uninstall the llmeter menu bar app: quit it, remove /Applications/Llmeter.app,
# unregister the Login Item, and remove the menubar venv.

set -euo pipefail

if [ "$(uname -s)" != "Darwin" ]; then
  echo "[llmeter] menu bar app is macOS-only; nothing to uninstall" >&2
  exit 0
fi

APP_DEST="/Applications/Llmeter.app"
LOGIN_ITEM_NAME="Llmeter"
MENUBAR_VENV="$HOME/.llmeter/menubar-venv"

osascript -e 'tell application "Llmeter" to quit' >/dev/null 2>&1 || true
pkill -f "/Applications/Llmeter.app" >/dev/null 2>&1 || true

osascript -e "tell application \"System Events\" to delete (every login item whose name is \"$LOGIN_ITEM_NAME\")" >/dev/null 2>&1 || true

rm -rf "$APP_DEST"
rm -rf "$MENUBAR_VENV"

echo "[llmeter] menu bar app removed"
