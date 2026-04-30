# PROGRESS — menubar-app branch

Tracking work to add a Mac menu bar surface to llmeter alongside the
existing localhost dashboard.

## 2026-04-29

- [x] Branch created: `menubar-app` off `main` at `a3482ae`.
- [x] Authored `SPEC.md` formalizing both surfaces (dashboard + menu bar) and
      the read-only-client design that has the menu bar share SQLite with
      the launchd-managed dashboard. Existing launchd service kept (lower-risk
      default; tradeoff documented).
- [x] Wrote `llmeter/menubar/queries.py` — single read-only helper that
      pulls today's totals, Claude vs Codex split, est. cost, and last
      session via `llmeter/db.py`. No duplicated SQL.
- [x] Wrote `llmeter/menubar/app.py` — rumps app: title shows compact today
      tokens, menu lists totals + last session + open-dashboard + refresh +
      quit. Polls every `LLMETER_MENUBAR_REFRESH_SEC` seconds (default 5).
- [x] Wrote `llmeter/menubar/__main__.py` so `python -m llmeter.menubar`
      launches the app from a venv.
- [x] Added `setup_menubar.py` for py2app bundling into `Llmeter.app`.
- [x] Added `requirements-menubar.txt` pinning `rumps` + `py2app` (kept out
      of the core `requirements.txt` to avoid forcing pyobjc on dashboard
      users).
- [x] Added `tests/test_menubar_queries.py` covering today totals, source
      split, est cost summing, last session, and empty-DB case.
- [x] Ran `pytest`: all tests pass (existing + new).
- [x] Updated `README.md` with a "Menu Bar App" section and dev/build
      instructions.
- [x] Committed in logical chunks. Pushed branch.

## Final blurb (for John)

Branch: **`menubar-app`** in `~/projects/llmeter`, pushed to origin.

What shipped:
- `SPEC.md` — first-class spec covering both dashboard and menu bar.
- `llmeter/menubar/` — rumps app, reuses `db.py` + `pricing.py`, no
  duplicated SQL.
- `setup_menubar.py` + `requirements-menubar.txt` — py2app build path.
- Tests for the menu bar query layer (5 cases).
- README updates.

How to try it locally:
```
cd ~/projects/llmeter
git checkout menubar-app
python3 -m venv .venv-menubar
. .venv-menubar/bin/activate
pip install -r requirements.txt -r requirements-menubar.txt

# quick run (no app bundle):
python -m llmeter.menubar

# build a real .app:
python setup_menubar.py py2app -A   # alias mode for fast iteration
open dist/Llmeter.app
```

Tested: `pytest` green (existing dashboard/parser tests + new menubar query
tests).

Untested: the rumps GUI loop and the py2app bundle on a clean machine — these
need a manual run. The query helper that the menu reads from is unit-tested.

Open follow-ups:
- Decide whether to keep the launchd dashboard or fold its FastAPI server
  into `Llmeter.app` (current default: keep launchd, additive). See SPEC
  "Open Questions".
- Standalone ingest in the menu bar (so dashboard isn't required).
- Cost/token threshold notifications.
- npm installer changes to optionally install the .app — not in this branch.

Nothing is deployed; your running `~/.llmeter` install is untouched.

---

## 2026-04-29 — Round 2: dead-simple npm install

John asked for the npm install path to also install the menu bar app — Mac
only is fine, dead simple. Done.

Changes:

- `bin/llmeter.js`
  - new flags `--no-menubar`, `--menubar-only` (mutually exclusive); existing
    `--no-open` preserved.
  - `install` now runs the dashboard install (unless `--menubar-only`) and
    then `scripts/install_menubar.sh` (unless `--no-menubar`).
  - `uninstall` now also runs `scripts/uninstall_menubar.sh` (quit app,
    remove `/Applications/Llmeter.app`, remove Login Item, remove
    `~/.llmeter/menubar-venv`) before removing `~/.llmeter/app`.
  - `status` reports menu bar app installed/running.
  - `start` / `stop` also start/stop the menu bar app.
  - Updated `--help` to document the new flags + new behavior.
- `scripts/install_menubar.sh` (new)
  - Creates `~/.llmeter/menubar-venv` (separate from dashboard venv).
  - Installs `requirements.txt` + `requirements-menubar.txt` into it.
  - Builds `Llmeter.app` via `python setup_menubar.py py2app -A` (alias mode,
    fast — references the source under `~/.llmeter/app`).
  - Idempotently quits any running instance, removes any prior bundle, and
    copies to `/Applications/Llmeter.app`.
  - Idempotently removes prior Login Item by name and registers a new one
    via `osascript`. If automation permission is missing, prints a clear
    fallback message instead of failing.
  - Launches the app via `open -a Llmeter`.
- `scripts/uninstall_menubar.sh` (new)
  - Quits the app, removes `/Applications/Llmeter.app`, removes the Login
    Item, removes `~/.llmeter/menubar-venv`.
- `requirements-menubar.txt` — pinned `setuptools<81` (py2app 0.28.8 still
  imports `pkg_resources`, removed in setuptools 81).
- `--menubar-only` decision: kept the flag but documented the tradeoff.
  Implementing a true ingest-only entrypoint (`python -m llmeter.ingest_only`)
  was non-trivial in the available time — ingest is currently invoked from
  inside the FastAPI server lifecycle. Tradeoff is documented in `SPEC.md`
  and the help text. v1 ships with `--menubar-only` skipping the dashboard
  service but not setting up an alternative ingest path.

Tested end-to-end on this Mac:

1. Backed up `~/.llmeter` → `~/.llmeter.bak.20260429-164921`.
2. Ran `node bin/llmeter.js install --no-open`. Result: dashboard reinstalled,
   `Llmeter.app` built and copied to `/Applications`, app launched (verified
   via `pgrep`).
3. `node bin/llmeter.js status` → reported dashboard `running/loaded`,
   menu bar app `installed and running`, dashboard HTTP 200.
4. `curl http://127.0.0.1:4001/api/today` → 200.
5. `node bin/llmeter.js uninstall`. Result: app process gone,
   `/Applications/Llmeter.app` removed, `~/.llmeter/app` removed,
   `~/.llmeter/menubar-venv` removed.
6. Restored `~/.llmeter` from backup, re-bootstrapped the launchd service.
   `launchctl print` shows `state = running`; HTTP 200 again.
7. `pytest` — 11/11 green.

What didn't work cleanly:

- Login Item registration via `osascript` requires Automation permission for
  the terminal/host process. On first run it may prompt or silently fail.
  The installer now degrades gracefully: prints a one-line fallback telling
  the user to either grant the permission or add the Login Item manually
  via System Settings. Bundle install + launch are unaffected.

How John can try it:

```
npx github:jawnty/llmeter#menubar-app install
```

That's the whole UX. Look for `⚡` in the menu bar; the dashboard opens
automatically. To revert:

```
npx github:jawnty/llmeter#menubar-app uninstall
```

Open follow-ups (unchanged from round 1):

- Standalone ingest entrypoint so `--menubar-only` actually ingests.
- Cost / token threshold notifications.
- Optional folding of dashboard into `Llmeter.app` (one process).

---

## 2026-04-29 — Round 3: kill the macOS permission prompt

Round 2's installer used `osascript` + System Events to register a Login
Item. That requires the user to grant Automation permission to the calling
terminal, which broke the "dead simple" promise. Swapped it for a plain
launchd LaunchAgent — fully scriptable, zero user permission grants.

Changes:

- `scripts/install_menubar.sh` — drops both `osascript ... System Events`
  calls. Writes `~/Library/LaunchAgents/com.llmeter.menubar.plist`
  (`Label=com.llmeter.menubar`, `RunAtLoad=true`, `KeepAlive=false`,
  `ProgramArguments=/usr/bin/open -a /Applications/Llmeter.app`,
  stdout/stderr → `~/.llmeter/logs/menubar.log`). Idempotently
  `launchctl bootout` any prior agent, then `bootstrap` + `kickstart`.
- `scripts/uninstall_menubar.sh` — replaces the Login Item delete with
  `launchctl bootout` + `rm -f` of the plist.
- `bin/llmeter.js` — `start` now uses the new `startMenubar()` helper that
  prefers `launchctl kickstart` of `com.llmeter.menubar`, falling back to
  `launchctl bootstrap` + `kickstart`, then `open -a Llmeter` as a final
  resort. `status` adds a `menu bar LaunchAgent: loaded / not loaded` line.
  `uninstall` fallback (when scripts aren't present) now bootouts + removes
  the plist instead of poking System Events. Help text mentions LaunchAgent.
  Removed the unused `LOGIN_ITEM_NAME` constant.
- README + SPEC.md updated to describe the LaunchAgent path; troubleshooting
  paragraph about granting Automation permission removed because it no
  longer applies.

Tested end-to-end on this Mac:

1. Backed up `~/.llmeter` → `~/.llmeter.bak.<ts>`.
2. `node bin/llmeter.js install --no-open` → dashboard reinstalled,
   `Llmeter.app` built and copied, LaunchAgent plist written, app launched.
   `launchctl print gui/$UID/com.llmeter.menubar` shows it loaded. App
   process visible via `pgrep`. **No automation permission prompt.**
3. `node bin/llmeter.js status` → dashboard `running/loaded`, menu bar
   `installed and running`, LaunchAgent `loaded`, dashboard HTTP 200.
4. `node bin/llmeter.js uninstall` → app gone, plist gone,
   `launchctl print` reports unknown service, `~/.llmeter/menubar-venv`
   gone, `~/.llmeter/app` gone.
5. Restored `~/.llmeter` from backup, re-bootstrapped the dashboard
   launchd service. HTTP 200 again. Backup deleted.
6. `pytest` — 11/11 green.

Try it (unchanged):

```
npx github:jawnty/llmeter#menubar-app install
```

No permission prompts, no manual steps.
