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
