"""rumps-based menu bar app.

Polls the local SQLite database every few seconds and renders a small
status menu. The dashboard process owns ingest; this app is a read-only
client. See SPEC.md.

Run from a venv that has rumps installed:

    pip install rumps
    python -m llmeter.menubar
"""

from __future__ import annotations

import os
import webbrowser

import rumps

from .. import config
from . import queries


REFRESH_SEC = float(os.environ.get("LLMETER_MENUBAR_REFRESH_SEC", "5"))


class LlmeterApp(rumps.App):
    def __init__(self):
        super().__init__("llmeter", title="⚡ —", quit_button=None)
        self._mi_today = rumps.MenuItem("Today: —")
        self._mi_fresh = rumps.MenuItem("Fresh input: —")
        self._mi_cache = rumps.MenuItem("Cache read: —")
        self._mi_claude = rumps.MenuItem("Claude: —")
        self._mi_codex = rumps.MenuItem("Codex: —")
        self._mi_cost = rumps.MenuItem("Est. cost: —")
        self._mi_last = rumps.MenuItem("Last: —")

        self.menu = [
            self._mi_today,
            self._mi_fresh,
            self._mi_cache,
            self._mi_claude,
            self._mi_codex,
            self._mi_cost,
            self._mi_last,
            None,  # separator
            rumps.MenuItem("Open dashboard", callback=self.open_dashboard),
            rumps.MenuItem("Refresh now", callback=self.refresh_now),
            None,
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]
        self._timer = rumps.Timer(self._on_tick, REFRESH_SEC)
        self._timer.start()
        self._refresh()

    def _on_tick(self, _sender):
        self._refresh()

    def _refresh(self):
        try:
            snap = queries.snapshot()
        except Exception as exc:  # noqa: BLE001 — show errors in the menu
            self.title = "⚡ ?"
            self._mi_today.title = f"Error: {exc}"
            return

        self.title = snap.title()
        self._mi_today.title = f"Today: {queries.fmt_int(snap.total_tokens)} tokens"
        self._mi_fresh.title = f"Fresh input: {queries.fmt_int(snap.input_tokens)}"
        self._mi_cache.title = f"Cache read: {queries.fmt_int(snap.cache_read_tokens)}"
        self._mi_claude.title = f"Claude: {queries.fmt_int(snap.claude_tokens)}"
        self._mi_codex.title = f"Codex:  {queries.fmt_int(snap.codex_tokens)}"
        self._mi_cost.title = f"Est. cost: {queries.fmt_cost(snap.cost_usd)}"
        self._mi_last.title = queries.fmt_last_session(snap.last_session)

    def open_dashboard(self, _sender):
        url = f"http://{config.host()}:{config.port()}"
        webbrowser.open(url)

    def refresh_now(self, _sender):
        self._refresh()


def main():
    LlmeterApp().run()


if __name__ == "__main__":
    main()
