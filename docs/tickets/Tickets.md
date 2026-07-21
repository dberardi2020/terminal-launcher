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
| TLA-0016 | Feature | P2 | cli | [**Non-interactive config CLI**](TLA-0016/TLA-0016.md) — `new`/`edit`/`pane-new` are prompt-driven, so nothing can create a pane or workspace in one call. Add flag- and stdin-JSON-driven variants for scripting, reproducible seeding, CI, and agent-driven setup. |
| TLA-0017 | Feature | P3 | tooling | [**GUI automation / demo hooks**](TLA-0017/TLA-0017.md) — no supported way to open the composer in a given state; the README screenshots needed a throwaway `evaluate_js` harness. `gui --load <workspace>` is the minimum, and is a good everyday path in its own right. |
| TLA-0018 | Feature | P3 | docs | [**Hosted browser demo (GitHub Pages)**](TLA-0018/TLA-0018.md) — the composer is one self-contained HTML file over a thin `window.pywebview.api` seam, so mocking that seam makes it a static "try it in your browser" page. A UI tour, not functional; the mock is the real long-term cost. |
| TLA-0020 | Feature | P3 | tooling | [**A family of management commands**](TLA-0020/TLA-0020.md) — `update`/`install`/`uninstall`/`repair`. Four per-platform installers today, no uninstall or update story, and a moved checkout silently breaks the baked-in `/restore` paths. Overlaps TLA-0012 and TLA-0010; first action is a merge decision. |
| TLA-0022 | Chore | P3 | packaging | **Drop `bin/terminal-launcher`:** now that `pyproject.toml` ships a `console_scripts` entry point (and `python -m terminal_launcher` covers the checkout case), the `bin/` shim is redundant. **Blocked on** the `/restore` installers, which currently invoke it — move them to the installed `terminal-launcher` (with a `python -m` fallback for checkout-only users), then delete `bin/` and its doc references. |
| TLA-0023 | Chore | P2 | quality | [**Audit error handling, reporting & logging**](TLA-0023/TLA-0023.md) — one ticket because both halves sweep the same call sites. Prompted by two "failure looked like success" defects in `/restore` (both now fixed). Covers failure propagation and the `DETECTED`/`RESTORED`/`UNKNOWN`/`ERROR` contract, the unwritten lenient-vs-strict rule, the stderr banner on every CLI run, verbosity control, double-reporting, and `restore.py`'s missing detect-path logging. |
| TLA-0024 | Chore | P3 | tooling | **Move the ticket board to GitHub Projects.** An in-repo MD+HTML board fit a private solo repo; a public one gets Issues/Projects for free — cross-links to commits and PRs, and no lockstep render to maintain. Needs a call on what migrates (Open rows, the Done history, `TLA-NNNN/` folders and their screenshots) and whether the `TLA-NNNN` IDs survive as labels. |

## Blocked

_(none)_

## Done

| ID | Type | Area | Title | Closed |
|---|---|---|---|---|
| TLA-0021 | Bug | backend | **Dock app leaked `PYTHONHOME`/`PYTHONPATH` into launched panes** — the `.app` set both to its own `Contents/Resources`, and because a cold start launches iTerm2 itself, every pane inherited them; any `python` in a pane resolved the bundle's stdlib (a `pipx`-installed `terminal-launcher` silently ran the stale bundled copy). Fixed three ways: `backend.scrub_bundled_python_env()` at both entry points (root cause, cold start); an `env -u PYTHONHOME -u PYTHONPATH` prefix on each pane command (covers an already-polluted iTerm2); and `packaging/install-macos.sh` now unsets both — the build itself failed (`No module named 'jaraco.functools'`) when run from a polluted pane, resolving setuptools out of the *bundle's* stdlib. 5 tests. **Verified end-to-end:** with the rebuilt `.app` installed, a pane launched from a polluted shell — with a probe value injected into `PYTHONPATH` — came up with **neither variable and no probe**, while a pane launched before the fix still shows both. | 2026-07-21 |
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
- **Keep rows short — length is the signal.** A row is a *pointer*: what the work is and
  why it matters, in a sentence or two. If the description outgrows that, the ticket has
  a breakdown in it — move the detail into `TLA-NNNN/TLA-NNNN.md` and link the row's
  title to it. Rationale, investigation notes, current-state inventories, and
  option-weighing all belong in the file, not the table. A board you have to scroll
  sideways to read has stopped being a board. **Done** rows are exempt — there the row
  *is* the record of what shipped, and it's on its way to `Archive/` anyway.
- **Screenshots:** fresh captures (e.g. from `/db-screenshot`) stage in the gitignored
  `Screenshots/` inbox; promote keepers into the ticket's own `TLA-NNNN/Screenshots/`.
- **Archiving:** closed items drop to **Done** above. When **Done** gets long, move rows
  to `Archive/Tickets.md`; a closed ticket that had a folder moves to `Archive/TLA-NNNN/`.
- Regenerate the HTML view after editing: `python docs/render.py docs/tickets/Tickets.md`.
