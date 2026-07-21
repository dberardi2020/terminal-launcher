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
