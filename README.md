# llmeter

Local live token-usage monitor for Claude Code and Codex.

llmeter reads the JSONL session logs that Claude Code and Codex already write,
stores usage in SQLite, and serves a local dashboard at
`http://127.0.0.1:4001`.

It does not require API key changes, shell aliases, or wrapping your editor.

![llmeter dashboard](docs/screenshots/dashboard.png)

![llmeter session detail](docs/screenshots/session-detail.png)

## What Works Today

llmeter currently supports:

- Claude Code: `~/.claude/projects/**/*.jsonl`
- Codex: `~/.codex/sessions/**/*.jsonl`

It can be expanded to other LLM tools later. The intended expansion path is a
thin monitoring layer that can sit above provider-normalization systems like
LiteLLM, while keeping the dashboard and storage model local.

## Install

Requirements: macOS, Python 3.11 or newer, and either Claude Code or Codex.

```bash
npx llmeter install
```

Then open:

```text
http://127.0.0.1:4001
```

That is it. The installer:

- copies llmeter into `~/.llmeter/app`
- creates `~/.llmeter/app/.venv`
- installs pinned Python dependencies from `requirements.txt`
- writes a launchd service for the installed app path
- starts llmeter now and on future logins
- opens the dashboard

Logs are written to:

```text
~/.llmeter/logs/llmeter.log
```

The SQLite database is written to:

```text
~/.llmeter/app/data/llmeter.db
```

If you are trying the current GitHub version before the npm package is
published, use:

```bash
npx github:jawnty/llmeter install
```

## Using llmeter

The dashboard shows:

- today's total tokens, turns, and reference API cost
- Claude Code vs. Codex token split
- hourly token bars in your local timezone
- session list with project, opening prompt, models, turns, and tokens
- per-turn details when you click a session
- live updates through server-sent events

The cost number is a reference estimate only. It uses approximate published API
prices so you can spot expensive sessions. It is not your real bill, especially
if you use subscription products.

## Menu Bar App (macOS)

llmeter ships a Mac status bar app as a second, additive surface. It shows
today's totals at a glance without opening a browser. The dashboard is the
deep view; the menu bar is the always-on glance view.

What it shows:

- compact token count in the menu bar (e.g. `⚡ 1.2M`)
- today's total tokens, Claude vs Codex split, reference cost
- last session summary (project · turns · tokens)
- "Open dashboard" → `http://127.0.0.1:4001`
- "Refresh now", "Quit"

It is a **read-only client of the same SQLite database** the dashboard
writes to. Ingest stays in the dashboard's launchd service. The menu bar
app polls the database every 5 seconds (override with
`LLMETER_MENUBAR_REFRESH_SEC`).

Build and run:

```bash
cd /path/to/llmeter
python3 -m venv .venv-menubar
. .venv-menubar/bin/activate
pip install -r requirements.txt -r requirements-menubar.txt

# fast iteration (alias mode, runs from source):
python setup_menubar.py py2app -A
open dist/Llmeter.app

# standalone bundle:
python setup_menubar.py py2app
```

Drag `dist/Llmeter.app` to `/Applications`. To launch on login: System
Settings → General → Login Items → add `Llmeter.app`. The dashboard's
launchd service is unrelated and unaffected.

You can also run the menu bar directly from a venv without bundling:

```bash
python -m llmeter.menubar
```

See `SPEC.md` for the full design rationale.

## Help Page

The running app includes a short Help page linked from the top right of the
dashboard:

```text
http://127.0.0.1:4001/docs
```

The Help page is intentionally shorter than this README so new users can get
unstuck without leaving the app.

## Stop Or Restart

Stop:

```bash
npx llmeter stop
```

Start:

```bash
npx llmeter start
```

Restart:

```bash
npx llmeter stop
npx llmeter start
```

Check status:

```bash
npx llmeter status
```

Remove the installed app:

```bash
npx llmeter uninstall
```

## Configuration

Most users do not need any configuration. llmeter infers paths from the checkout
location and from the standard Claude Code and Codex log directories.

Advanced overrides:

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLMETER_HOST` | `127.0.0.1` | bind address |
| `LLMETER_PORT` | `4001` | dashboard port |
| `LLMETER_DB_PATH` | `data/llmeter.db` | SQLite database path |
| `LLMETER_DATA_DIR` | `data` | database directory when `LLMETER_DB_PATH` is unset |
| `LLMETER_LOG_DIR` | `~/.llmeter/logs` | launchd log directory used by the installer |
| `LLMETER_CLAUDE_GLOB` | `~/.claude/projects/**/*.jsonl` | Claude Code log glob |
| `LLMETER_CODEX_GLOB` | `~/.codex/sessions/**/*.jsonl` | Codex log glob |

Example:

```bash
LLMETER_PORT=4010 bash scripts/install.sh
```

## LiteLLM And Security

llmeter's v1 ingestion path for Claude Code and Codex reads local log files. It
does not proxy those tools through LiteLLM.

The broader design treats llmeter as the dashboard/storage layer above local LLM
tooling. For tools that need a proxy or provider-normalization layer, the
expected expansion path is a LiteLLM-backed ingestion source. That LiteLLM path
should use exact pinned versions, not floating installs.

LiteLLM has had security-sensitive issues, so be conservative: pin versions,
watch upstream advisories, do not expose proxies publicly, and run it at your own
risk. Pinning reduces supply-chain drift, but it does not make any proxy
automatically safe.

## Development

Set up dependencies:

```bash
git clone https://github.com/jawnty/llmeter.git
cd llmeter
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Run locally:

```bash
python -m llmeter
```

Run tests:

```bash
pytest
```

Test the npm wrapper from the checkout:

```bash
node bin/llmeter.js --help
npm pack --dry-run
```

## Data Model

llmeter stores:

- `sessions`: source, project, working directory, opening prompt, models
- `turns`: timestamp, token counts, local day/hour bucket, reference cost
- `file_offsets`: last ingested byte offset for each JSONL file

The database is local SQLite. No usage data is sent anywhere by llmeter.

## Roadmap

- Gemini CLI ingestion
- multi-day comparison views
- project-level rollups
- cache hit-rate dashboard
- model-tier suggestions
- optional LiteLLM-backed ingestion for tools that need a proxy layer
