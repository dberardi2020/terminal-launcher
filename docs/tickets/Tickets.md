# Terminal Launcher — Tickets

A lightweight backlog — persist and review open items without a ticketing system.

## In progress

_(none)_

## Open

| ID | Type | Pri | Area | Title |
|---|---|---|---|---|
| TLA-0001 | Chore | P2 | tests | Integration tests: launch each layout, assert window/pane structure + frames via iTerm2 API read-back |
| TLA-0003 | Chore | P3 | packaging | Ad-hoc sign the py2app bundle to stop TCC/Automation re-prompting after each rebuild |
| TLA-0004 | Feature | P3 | ux | Themes: appearance is hardcoded One Dark / Menlo 13; the dynamic profile is fully configurable |
| TLA-0005 | Bug | P3 | backend | Cold-start window restoration reopens prior tool windows on relaunch (benign; left alone to avoid closing real work) |
| TLA-0007 | Bug | P2 | ux | [Panes list overflows on long paths: wrapped entries (Private KB, Email HQ) push their edit/delete icons out of the shared right-aligned column, past the panel edge](TLA-0007/) |
| TLA-0010 | Chore | P2 | packaging | Streamline pushing updates to the installed Dock app so code changes don't need a full py2app rebuild + reinstall each time — evaluate py2app **alias mode** (`python setup.py py2app -A`), a symlinked package, or launching the GUI from source. |
| TLA-0012 | Feature | P2 | packaging | Design the **install/setup** flow and the **maintenance/update** flow for going live as an ongoing project — first-run setup (deps, iTerm2, Automation grant, config seed) + a repeatable release/update path (version bump, rebuild, swap). The umbrella over the narrower dev-loop fix in TLA-0010. |
| TLA-0013 | Feature | P2 | ux | Add a visual loading animation during launch so the composer doesn't look frozen while the backend spawns windows and injects `/color` — the launch runs on a background thread with color-injection sleeps, leaving the window idle for a few seconds. |
| TLA-0014 | Feature | P2 | backend | **Multi-monitor placement:** slot rects derive from the *primary* monitor's work area only (`SPI_GETWORKAREA` on Windows, main display on macOS), so a workspace always lands on the primary display. Add per-monitor targeting — relevant now that the PC is a multi-display setup. |
| TLA-0015 | Feature | P3 | ux | **Revisit Windows Terminal tab tinting:** `--tabColor <pane hex>` was implemented then dropped ([ADR 0008](../decisions/0008-one-window-per-pane-and-windows-terminal-backend.md)) — the composer's swatch hexes don't read well against wt's own theming. Needs a palette tuned for `wt`, not a reuse of the pane colours. |
| TLA-0016 | Feature | P2 | cli | **Non-interactive config CLI:** `new`/`edit`/`pane-new` are prompt-driven. Add flag- and/or stdin-JSON-driven variants so panes and workspaces can be created/edited without prompts — e.g. `pane-new --name API --color green --target ~/src/api --model opus`, `workspace set Full-Stack --layout quad --slots api,web,infra,tests`. Enables scripting, reproducible seeding, CI, and agent-driven setup (strengthens the "hand it to your coding agent" story). Thin validated wrapper over `config.save` since the config is already one JSON file. |
| TLA-0017 | Feature | P3 | tooling | **GUI automation / demo hooks:** a supported way to drive the composer into a given state instead of the ad-hoc `evaluate_js` staging used to produce the README demo shots. Minimum `gui --load <workspace>` (open with a workspace pre-loaded — also a nice everyday UX); optionally `--edit-slot <n>` / `--panel panes` and a screenshot harness for UI tests. Replaces the throwaway staging script and makes demo/screenshot generation repeatable. |
| TLA-0018 | Feature | P3 | docs | **Hosted browser demo (GitHub Pages):** the composer is `web/builder.html` over a thin `window.pywebview.api` seam — stub that API with an in-memory JS mock (fake `get_state`, no-op `save`/`launch`) and it runs as a static "try it in your browser" page linkable from the README. Caveats: it's a **UI tour, not functional** (a browser can't spawn terminals), and the mock must be kept in sync with the real API. Nice-to-have, not blocking; screenshots cover the immediate need. |
| TLA-0020 | Feature | P3 | tooling | **Ship a family of management skills/commands:** consider Claude Code skills (and/or CLI verbs) covering the app lifecycle — `tl-update`, `install`, `uninstall`, `reinstall`, `repair`, etc. Today setup and updates are manual and scattered per-platform (`packaging/install-macos.sh`, `integrations/claude-code/install.{sh,ps1}`), and a moved checkout silently breaks the baked-in `/restore` paths. A consistent, discoverable family would cover first-run setup, updating an installed build, clean removal, and repairing a broken install (missing venv, stale paths, Automation re-prompt). Overlaps **TLA-0012** (install/setup + update flow) and **TLA-0010** (streamline dock updates) — decide whether this supersedes or complements them. |
| TLA-0021 | Bug | P2 | backend | **Dock app leaks `PYTHONHOME`/`PYTHONPATH` into launched panes:** the installed `.app` sets both to `/Applications/Terminal Launcher.app/Contents/Resources` (its bundled interpreter) and panes it launches **inherit them** — so *any* Python run in a launched pane imports the `.app`'s bundled `terminal_launcher` instead of the real one. Verified: a `pipx`-installed `terminal-launcher` silently ran the stale bundled copy until the vars were scrubbed. This is the root cause behind every `env -u PYTHONHOME -u PYTHONPATH` workaround (`/restore`, both installers). Fix at the source — scrub both from the environment handed to spawned panes (backend launch path, or `gui.py` before handoff) — then retire the workarounds. |
| TLA-0022 | Chore | P3 | packaging | **Drop `bin/terminal-launcher`:** now that `pyproject.toml` ships a `console_scripts` entry point (and `python -m terminal_launcher` covers the checkout case), the `bin/` shim is redundant. **Blocked on** the `/restore` installers, which currently invoke it — move them to the installed `terminal-launcher` (with a `python -m` fallback for checkout-only users), then delete `bin/` and its doc references. |
| TLA-0023 | Chore | P2 | quality | **Audit error handling, reporting & logging.** Kept as one ticket because both halves sweep the *same* call sites (`_paste_command`, `cmd_restore`, `backend.launch`, the GUI bridge all log *and* report). Motivated by two "failure looked like success" defects found in a single feature, both in code that read fine: Windows `_paste_command` only *logged* a miss while `cmd_restore` printed `RESTORED` regardless (user told "Restored X" for a paste that never happened); and macOS `restore_current` let exceptions escape into the iterm2 runner, which prints a raw traceback and exits 1 — bypassing the `ERROR` branch entirely. **(a) Errors:** sweep every failure path — does it propagate, is failure distinguishable from success, is the message actionable, is the documented contract honoured (`DETECTED`/`RESTORED`/`UNKNOWN`/`ERROR` + exit codes)? Cover `backend.launch` (per-slot failure mid multi-pane launch), the pywebview bridge (pywebview turns exceptions into silently-rejected promises — hence `gui.Api`'s tracer), and CLI exit codes. Write down and apply the **lenient-vs-strict convention**: launch-time `/color` is deliberately lenient (one pane shouldn't abort a quad launch), `restore` is strict. **(b) Logging:** `diag.setup()` attaches a stderr handler, so `INFO --- diag ready ---` prints on *every* CLI run — noise the `/restore` command must parse around. Audit levels/destinations, keep stdout clean for machine-readable output, add verbosity control (`--verbose`/`--quiet` or env var), stop double-reporting (raised failures shouldn't *also* log a warning), sanity-check rotation, and ensure pane-launch failures log enough context to diagnose after the fact. Split if (a) alone proves large enough. |

## Blocked

_(none)_

## Done

| ID | Type | Area | Title | Closed |
|---|---|---|---|---|
| TLA-0006 | Chore | docs | Sync docs to the iTerm2 pivot: new [ADR 0007](../decisions/0007-iterm2-backend-and-real-gap-layouts.md), README/concept updates, version bump (commit `79a0aff`) | 2026-07-17 |
| TLA-0009 | Feature | tooling | `db-restore` — global skill restoring pane identity (`/color` + `/rename`) from the TL `panes` config, matched by cwd, via the iTerm2 API. Script `~/.claude/scripts/db-restore.py` + command `db-restore.md` | 2026-07-17 |
| TLA-0011 | Feature | backend | Dropped WezTerm entirely; unified on the native iTerm2 separate-window backend (non-macOS raises a clear "Windows Terminal planned" error). Branch `unify-mac-and-strip-wezterm` — verified: 21 tests, quad → 4 tiled windows, `/color`, GUI | 2026-07-21 |
| TLA-0008 | Bug | ux | GUI backend gate-key renamed `wezterm` → `terminal` (badge "No terminal backend"), so the Launch gate no longer misnames iTerm2. Fixed alongside the WezTerm strip | 2026-07-21 |
| TLA-0002 | Chore | backend | Obsolete — `wezterm.py` removed with the WezTerm strip (TLA-0011), so its duplicate `SPLIT_PLAN` is gone; `layouts.py` is now the sole source | 2026-07-21 |
| TLA-0019 | Chore | backend | Verified `/restore` on Windows end-to-end: detection (3/3 panes, longest-match, `WT_SESSION` sentinel, UNKNOWN), live `/color` + `/rename` both landing and submitting in the correct `wt` window, no launch-time regression from the `_paste_command` extraction, clipboard preserved, and `install.ps1` generating a working command line. Fixed three defects found in review — ambiguous multi-window fallback, clipboard leak on the bail-out path, and injection failures reported as success — plus dropped `install.ps1`'s macOS-inherited venv requirement (Windows needs no third-party deps). See [ADR 0009](../decisions/0009-restore-pane-identity.md) | 2026-07-21 |

---

## Conventions

- **Source of truth is this file** (board-first). Edit the tables directly.
- **IDs** are `TLA-NNNN`, one sequence, assigned in creation order (not priority).
- **Type:** Bug · Feature · Chore (Chore = tests, refactors, packaging, docs — housekeeping).
- **Statuses:** In progress · Open · Blocked · Done. **Priority:** P1 (soon) → P3 (someday).
- A ticket gets a folder **only when it has artifacts or needs a longer write-up** —
  `TLA-NNNN/` beside this file, linked from its title. Evidence goes under
  `TLA-NNNN/Screenshots/`; an optional `TLA-NNNN/TLA-NNNN.md` holds the breakdown.
  Trivial tickets are just a row here.
- **Screenshots:** fresh captures (e.g. from `/db-screenshot`) stage in the gitignored
  `Screenshots/` inbox; promote keepers into the ticket's own `TLA-NNNN/Screenshots/`.
- **Archiving:** closed items drop to **Done** above. When **Done** gets long, move rows
  to `Archive/Tickets.md`; a closed ticket that had a folder moves to `Archive/TLA-NNNN/`.
- Regenerate the HTML view after editing: `python docs/render.py docs/tickets/Tickets.md`.
