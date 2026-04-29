# tokmon

Local live token-usage monitor for Claude Code and Codex.

Reads the JSONL session logs the CLIs already write — no proxy, no env vars,
no API key changes. Aggregates into SQLite and serves a live dashboard at
**http://localhost:4001**.

## Install

```bash
bash scripts/install.sh
```

This:
1. Creates `.venv` with pinned deps from `requirements.txt`
2. Installs the launchd agent at `~/Library/LaunchAgents/com.tokmon.monitor.plist`
3. Starts it (and re-starts on every login)

Logs: `~/.openclaw/logs/tokmon.log`. DB: `data/tokmon.db`.

## Stop / start

```bash
launchctl unload ~/Library/LaunchAgents/com.tokmon.monitor.plist
launchctl load   ~/Library/LaunchAgents/com.tokmon.monitor.plist
```

## What it shows

- **Today's totals** — tokens, turn count, reference cost, Claude vs. Codex split
- **Hourly bar chart** — 24 bars, your local timezone
- **Session list** — start time, source, project, opening prompt, totals, models
- **Session drill-down** — per-turn breakdown when you click a row
- **Live updates** — SSE pushes a refresh whenever new turns are detected (poll cadence: 3s)

## Data sources

| CLI         | Path                                           |
|-------------|------------------------------------------------|
| Claude Code | `~/.claude/projects/**/*.jsonl`                |
| Codex       | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` |

## Design choices (for v1, may revisit)

- **Cost is a reference number, not a real charge.** John pays subscription rates
  for Claude Code and Codex. The `$` figures are calculated against published
  list API prices so you can see *what this would have cost on metered API* —
  useful for spotting expensive sessions, not for accounting.
- **SQLite from day 1.** Hourly slicing across many sessions is awkward over raw
  JSONL.
- **Localhost-only, no auth.** Bound to `127.0.0.1:4001`.
- **Local timezone for buckets.** Hour bars + day rollups use the system TZ.
- **Subagent files (`isSidechain: true`) are tagged but included.** They share
  the parent session id when present.
- **Codex sessions before 2025-09-06 (token_count event commit) are ignored**
  for token math — they have no usage data. The session row may still appear
  if newer turns exist for the same id.

## Pricing table

Pricing is hardcoded in `tokmon/pricing.py`. It's approximate, will drift,
and is labeled as such in the UI. Update the dict when major frontier
prices change.

## Deferred to v1.1

- Gemini CLI ingestion (log format less stable; revisit)
- Cache hit-rate dashboard
- Model-tier rightsizing suggestions ("this Opus session looked like a Haiku job")
- Multi-day comparison view
- Project-level rollups beyond the session table
