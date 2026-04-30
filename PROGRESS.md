# PROGRESS — 2026-04-29 / 2026-04-30

## Status Summary

llmeter is **shipped and live on npm at v0.2.1**, with a clean GitHub repo at
`github.com/jawnty/llmeter`, a working dashboard + macOS menu bar app, and a
publicly tweeted launch post. The first user (Mukund) hasn't been pinged yet
but the install command (`npx llmeter install`) is verified end-to-end on
John's Mac.

## What Was Done This Session

### Renamed the project: `tokmon` → `llmeter`

The npm name `tokmon` was already taken by an unrelated TUI dashboard published 3 days prior. Renamed everything before the first user touched it:

- npm package name + bin name + version → `llmeter`
- Python module `tokmon/` → `llmeter/`
- Working folder `/Users/john/projects/tokmon` → `/Users/john/projects/llmeter`
- launchd plist `com.tokmon.monitor` → `com.llmeter.monitor`
- Env var prefix `TOKMON_` → `LLMETER_`
- App install dir `~/.tokmon/app` → `~/.llmeter/app`
- Default log dir `~/.openclaw/logs` → `~/.llmeter/logs` (was John-specific, removed for public package)
- GitHub repo renamed (with redirect): `github.com/jawnty/tokmon` → `github.com/jawnty/llmeter`
- Memory dir copied from `-Users-john-projects-tokmon/memory/` → `-Users-john-projects-llmeter/memory/`

### Fixed a real FD-leak bug (v0.1.1)

`llmeter/db.py:connect()` returned a raw `sqlite3.Connection`. The `with` block in the FastAPI route handlers committed but never closed — sqlite3 connections leaked one FD per request. After ~hours of uptime the service wedged with `unable to open database file` and HTTP requests got connection-reset.

Fix: turned `connect()` into a `@contextmanager` that closes in `finally`. Verified: 63 FDs before / 63 FDs after 200 requests.

### Polished the dashboard

- Removed local `/docs` Help page; Help link now opens the GitHub README in a new tab. (README is the source of truth; one fewer doc to keep in sync.)
- Removed hover color-change on the hourly bar chart (was implying clickability when it does nothing).
- Re-captured `docs/screenshots/dashboard.png` and `session-detail.png` against the renamed live data.

### Merged menubar-app → main (v0.2.0)

The `menubar-app` branch (created in a parallel codex session, not by me) was 9 commits ahead with a rumps-based macOS menu bar app. Merged with `--no-ff`, ran tests (11/11 pass), updated README install bullets to mention both surfaces, fixed a stale "before npm is published" line, bumped to 0.2.0, pushed.

### Added `--version` / `-v` flag (v0.2.1)

So users reporting bugs can paste `npx llmeter --version`. Reads from `package.json`, no hardcoding. Bumped to 0.2.1, published.

### Found the codex jam-session origin notes

The other agent suggested **repositioning** llmeter from "Claude Code AND Codex" (equal halves) to "Claude Code first-class, with Codex included." Reasoning: makes the value prop clearer for single-tool users (like Mukund). **This change is NOT yet applied** — README and package.json description still lead with both as equal halves.

### Marketed it (in progress)

- Identified target tweets to reply to (Burkov, Guri Singh, Shruti Codes, VoxVex, etc. — see "What's Next").
- Drafted three origin-story tweet variants. John posted his own version at `https://x.com/jawnty/status/2049719852106158122`. Tweet has weaknesses I flagged: "OpenClaw" jargon in line 1, `http://` instead of `https://`, best line buried at bottom, no screenshot confirmed.

## Active State

### Live and verified
- npm: `llmeter@0.2.1` (versions: 0.1.0, 0.1.1, 0.2.0, 0.2.1)
- GitHub: `https://github.com/jawnty/llmeter` — public, latest commit `9ad37c3 v0.2.1: add --version / -v flag`
- John's Mac: dashboard service + menubar app both running. Dashboard at `http://127.0.0.1:4001`. Menubar `⚡` icon shows live tokens.
- Tweet: `https://x.com/jawnty/status/2049719852106158122`

### npm publish flow (memorized)

`npm publish` requires a fresh web-auth login first — John's account uses Touch ID/passkey, NOT TOTP. Do NOT prompt for a 6-digit OTP. Workflow:

```bash
npm login --auth-type=web   # opens browser, Touch ID
npm publish                 # token reused
```

This is documented in memory: `~/.claude/projects/-Users-john-projects-llmeter/memory/npm-publish-2fa.md`.

### Known gaps / open issues
- **Positioning not updated.** Codex suggested "Local live token-usage monitor for LLM coding tools" (broader). README + `package.json` description still say "Local token usage monitor for Claude Code and Codex." Decision pending from John.
- **Anyone who installed v0.1.0** (which had the FD leak) needs to reinstall to pick up the fix. No external users yet so this is moot, but worth noting.
- **The current Claude Code session was born in `/Users/john/projects/tokmon`** — its log lines record cwd as the old path. The dashboard correctly shows it as project=`tokmon` because `db.upsert_session` does `COALESCE(sessions.project, ...)` (first-write-wins). New sessions in `~/projects/llmeter/` will show as project=`llmeter`. This is accurate history, not a bug.
- **Marketing follow-up posts not drafted yet.** I suggested: (1) screenshot reply to John's tweet, (2) 1-2 insight follow-ups with specific numbers, (3) reactive replies to Burkov/Guri/Shruti. None done.

### External dependencies
- npm registry: `llmeter` slug owned by `jawnty`
- GitHub: `jawnty/llmeter` public repo
- launchd services on John's Mac: `com.llmeter.monitor` (dashboard) + `com.llmeter.menubar`
- Two venvs: `~/.llmeter/app/.venv` (dashboard) + `~/.llmeter/menubar-venv` (rumps)
- SQLite DB: `~/.llmeter/app/data/llmeter.db`

## What's Next

### Likely soon
1. **Apply the positioning tweak** (or explicitly reject it). Two-line change: README tagline + `package.json` description. Codex's suggestion was: lead with Claude Code first-class, frame Codex as included rather than equal half.
2. **Ping Mukund** with the install command — John was about to do this. After 24-72h of soak, fix whatever he finds, ship 0.2.2 if needed.
3. **Twitter follow-ups** to John's launch post:
   - Screenshot reply (menu bar `⚡` cropped tight, OR dashboard with eye-popping number) — almost certainly the highest-leverage move.
   - 1-2 insight tweets (e.g., "X% of my tokens were just Claude re-reading conversation," "Opus is N× more expensive per turn than Haiku for me").
4. **Reactive replies** to specific tweets (drafts not committed; ranked tier-1 list in conversation):
   - https://x.com/burkov/status/2012036165512184178 (manually calculating his shadow bill)
   - https://x.com/heygurisingh/status/2043907795972698218 (amplifying competitor TUI codeburn)
   - https://x.com/Shruti_0810/status/2043983455948812345 (same as Guri)

### Eventually
5. **Show HN post** — Tuesday/Wednesday morning Pacific. Hook: "subscription users have no visibility into their shadow bill."
6. **Awesome-list submissions** — `hesreallyhim/awesome-claude-code`, `jqueryscript/awesome-claude-code`, `rohitg00/awesome-claude-code-toolkit`. Cheap distribution.
7. **Roadmap items from README**: Gemini CLI ingestion, multi-day comparison views, project-level rollups, cache hit-rate dashboard, model-tier suggestions, optional LiteLLM-backed ingestion.
8. **A "weekly receipt" shareable image** (Spotify-Wrapped style) — built-in viral artifact.

### Watch for
- John's tweet engagement: `https://x.com/jawnty/status/2049719852106158122`
- New GitHub issues / npm install errors from early users
- New competitors in the niche — David Ilie's `tokmon@0.11.x` is iterating fast on the TUI side

## Key Decisions Made

- **Renamed before launch, not after.** npm name was the trigger but the project name itself collided. Cost was lowest pre-user.
- **Used `@contextmanager` not `closing()`** for the sqlite3 fix. Single function, cleaner stack traces, no `contextlib.closing` import.
- **Removed local `/docs` page** rather than maintaining it. README is the single source of truth.
- **Bumped 0.1.1 → 0.2.0 for menubar** (real new feature), not 0.1.2. Followed by 0.2.1 for the `--version` flag (tiny addition).
- **Kept `~/.llmeter/logs` (neutral) over `~/.openclaw/logs`** in the public default. The latter was John-specific; would have leaked his personal infra naming to every install.
- **Did not publish positioning change** without John's explicit approval, despite codex recommending it.
- **Memory carried forward at folder-rename time** — both the old `npm-publish-2fa.md` and a new `project-renamed-from-tokmon.md` now live in `-Users-john-projects-llmeter/memory/`.

## Key Files

- `bin/llmeter.js` — npm wrapper (install/start/stop/status/uninstall + `--version`)
- `llmeter/server.py` — FastAPI app (dashboard + JSON API + SSE)
- `llmeter/db.py` — `@contextmanager` connection wrapper, schema
- `llmeter/menubar/app.py` — rumps app
- `llmeter/menubar/queries.py` — read-only query helpers (no duplicated SQL)
- `scripts/install.sh` — dashboard launchd installer
- `scripts/install_menubar.sh` — menubar LaunchAgent installer (no py2app, no permission prompts)
- `package.json` — version 0.2.1, files list includes `requirements-menubar.txt`
- `SPEC.md` — design spec covering both surfaces
- `ARCHIVE.md` — prior PROGRESS.md (menubar build history)
