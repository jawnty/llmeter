# llmeter — Spec

Local live token-usage monitor for Claude Code and Codex on macOS.

llmeter ingests JSONL session logs that Claude Code and Codex already write,
stores normalized usage in a local SQLite database, and exposes that data
through two surfaces:

1. A localhost web dashboard at `http://127.0.0.1:4001`.
2. A native macOS **menu bar app** for at-a-glance numbers without leaving
   the keyboard.

Both surfaces are first-class. They share the same database and pricing logic.
The dashboard is the deep view; the menu bar is the always-on glance view.

---

## Goals

- Zero-config local-only usage tracking for Claude Code + Codex.
- No API key changes, no shell aliases, no editor wrapping.
- Two surfaces over one source of truth (SQLite).
- Reference cost estimate per turn, not a billing system.

## Non-Goals

- Multi-user / hosted service.
- Real billing reconciliation against subscription products.
- Cross-platform parity. macOS only for v1.

---

## Architecture

```
Claude Code logs     ┐
~/.claude/...        │
                     ├─►  ingest (tail JSONL) ──►  SQLite ──►  ┬─►  FastAPI dashboard (127.0.0.1:4001)
Codex logs           │    llmeter/ingest.py        ~/.llmeter   │
~/.codex/sessions/   ┘    llmeter/parser_*.py      /app/data/   └─►  rumps menu bar app (Llmeter.app)
                                                   llmeter.db
```

### Storage

SQLite at `~/.llmeter/app/data/llmeter.db` (overridable via `LLMETER_DB_PATH`).
Schema lives in `llmeter/db.py`. Both surfaces query through that module — no
duplicated SQL.

Tables: `sessions`, `turns`, `file_offsets`. See `llmeter/db.py` for canonical
schema.

### Ingest

A background tailer reads new bytes from each tracked JSONL file and inserts
turns. Dedup is by `raw_uuid`. Ingest is owned by exactly one process at a
time to avoid double-counting.

### Pricing

`llmeter/pricing.py` produces a reference USD estimate per turn from approximate
published API rates. It is not a bill.

---

## Surface 1 — Dashboard (existing)

FastAPI server at `http://127.0.0.1:4001`. Shows:

- Today's total tokens, turns, reference cost.
- Claude Code vs Codex token split.
- Hourly token bars in local time.
- Session list + per-turn detail.
- Live updates over server-sent events.

Launched by a launchd LaunchAgent installed by `npx llmeter install`.

## Surface 2 — Menu Bar App (new)

Native macOS status bar app, packaged as `Llmeter.app` via py2app.
Built with [rumps](https://github.com/jaredks/rumps) (a thin pyobjc wrapper).

### What it shows

The menu bar title is a compact token count for today, e.g. `⚡ 1.2M`.

Clicking the icon opens a menu with:

- `Today: 1,234,567 tokens` — disabled header
- `Claude: 800,123` — disabled
- `Codex:  434,444` — disabled
- `Est. cost: $4.12` — disabled
- `Last session: appmint · 12 turns · 84,210 tok` — disabled
- separator
- `Open dashboard` — opens `http://127.0.0.1:4001` in default browser
- `Refresh now` — force re-query
- separator
- `Quit`

Refreshes automatically every 5 seconds. No SSE — simple polling against the
local SQLite is plenty fast and avoids coupling the menu bar to the FastAPI
process lifecycle.

### State sharing — read-only client

The menu bar app is a **read-only client of the same SQLite database** that
the dashboard's launchd service writes to.

- Ingest stays in the existing launchd-managed FastAPI service (the writer).
- The menu bar app opens the SQLite file in read mode and queries through
  `llmeter/db.py` and a new `llmeter/menubar/queries.py` helper.
- This avoids two ingest loops fighting over offsets and lets the menu bar
  app start/stop independently of the dashboard.

Tradeoff noted: if a user wants to run **only** the menu bar (no dashboard),
they currently still need the launchd service running for ingest. Standalone
ingest in the menu bar app is a future option (`LLMETER_MENUBAR_INGEST=1`)
but not v1.

### Launching — npm installer is the canonical path

`npx llmeter install` installs both surfaces in a single command. For Mac
users this is the only thing they should ever need to run.

The installer:

1. Stages source at `~/.llmeter/app`.
2. Builds the dashboard venv at `~/.llmeter/app/.venv` and writes the
   launchd LaunchAgent `com.llmeter.monitor`.
3. Builds a separate menu bar venv at `~/.llmeter/menubar-venv` (rumps +
   py2app), kept separate so pyobjc/py2app don't bloat the dashboard env.
4. Runs `python setup_menubar.py py2app -A` (alias mode — fast, references
   the installed source) to produce `Llmeter.app`.
5. Copies the bundle to `/Applications/Llmeter.app` (idempotent: removes
   any prior bundle first).
6. Registers it as a Login Item via `osascript`/System Events
   (idempotent: removes any prior entry with the same name first).
7. Launches the app and opens the dashboard.

Install flags:

- `--no-menubar` — install only the dashboard.
- `--menubar-only` — install only the menu bar app. Ingest currently lives
  inside the dashboard service, so without the dashboard the menu bar will
  show stale data. Tradeoff is intentional: a standalone ingest entrypoint
  (`python -m llmeter.ingest_only`) is in the open-questions list but not
  v1; keeping a single ingest path avoids two writers competing for file
  offsets.
- `--no-open` — do not open the browser at the end.

The dashboard launchd service is **kept** as the canonical ingest owner.
Removing it would force a separate ingest mechanism just for the menu bar
app. Additive integration is the lower-risk default.

Manual / development build is preserved (see README "Development") for
hacking without the npm flow:

```
python3 -m venv .venv-menubar
. .venv-menubar/bin/activate
pip install -r requirements.txt -r requirements-menubar.txt
python -m llmeter.menubar          # run from source
python setup_menubar.py py2app -A  # alias-mode .app
```

### Configuration

Honors the same env vars as the dashboard:

- `LLMETER_DB_PATH` — read this database
- `LLMETER_PORT` / `LLMETER_HOST` — used to build the "Open dashboard" URL

New:

- `LLMETER_MENUBAR_REFRESH_SEC` — refresh interval, default 5

---

## Testing

- Existing dashboard + parser tests stay green.
- New tests in `tests/test_menubar_queries.py` exercise the query helper
  against a temp SQLite file with seeded rows.
- The rumps GUI loop is not unit-tested (it's a thin shell over the query
  helper). Manual smoke test: build the .app, run it, check the menu.

---

## Open Questions / Future

- Standalone ingest mode for the menu bar app (no dashboard required).
- Notifications when a session crosses a token or cost threshold.
- Per-source toggles in the menu (hide Codex, etc.).
- Replace launchd dashboard with a unified `Llmeter.app` that hosts both
  the menu bar and the FastAPI server in-process. Deferred — the current
  split keeps blast radius small.
