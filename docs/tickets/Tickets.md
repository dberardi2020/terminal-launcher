# Terminal Launcher — Tickets

A lightweight backlog — persist and review open items without a ticketing system.

## In progress

_(none)_

## Open

| ID | Type | Pri | Area | Title |
|---|---|---|---|---|
| TLA-0001 | Chore | P2 | tests | Integration tests: launch each layout, assert window/pane structure + frames via iTerm2 API read-back |
| TLA-0002 | Chore | P2 | backend | Reconcile `wezterm.py`'s own `SPLIT_PLAN` with `layouts.py` (single source of truth) — see [ADR 0007](../decisions/0007-iterm2-backend-and-real-gap-layouts.md) |
| TLA-0003 | Chore | P3 | packaging | Ad-hoc sign the py2app bundle to stop TCC/Automation re-prompting after each rebuild |
| TLA-0004 | Feature | P3 | ux | Themes: appearance is hardcoded One Dark / Menlo 13; the dynamic profile is fully configurable |
| TLA-0005 | Bug | P3 | backend | Cold-start window restoration reopens prior tool windows on relaunch (benign; left alone to avoid closing real work) |
| TLA-0007 | Bug | P2 | ux | [Panes list overflows on long paths: wrapped entries (Private KB, Email HQ) push their edit/delete icons out of the shared right-aligned column, past the panel edge](TLA-0007/) |
| TLA-0008 | Bug | P3 | ux | GUI `get_state()` reports launch-availability under a `wezterm` key even when the active backend is iTerm2, so the "WezTerm not found" badge can misname the backend (`terminalName` already carries the real name — gate/label on that instead) |

## Blocked

_(none)_

## Done

| ID | Type | Area | Title | Closed |
|---|---|---|---|---|
| TLA-0006 | Chore | docs | Sync docs to the iTerm2 pivot: new [ADR 0007](../decisions/0007-iterm2-backend-and-real-gap-layouts.md), README/concept updates, version bump (commit `79a0aff`) | 2026-07-17 |

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
