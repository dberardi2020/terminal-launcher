# Terminal Launcher — Tickets

A lightweight backlog — persist and review open items without a ticketing system.

- **Source of truth is this file** (board-first). Edit the tables directly.
- **IDs** are `TLA-NNNN`, assigned in creation order (not priority).
- **Statuses:** In progress · Open · Blocked · Done. **Priority:** P1 (soon) → P3 (someday).
- A ticket gets a folder **only when it needs a breakdown** — `TLA-NNNN/index.md`
  beside this file, linked from its title. Trivial tickets are just a row here.
- Closed items drop to **Done** below; split to `Archive.md` if it gets long.
- Regenerate the HTML view after editing: `python docs/render.py docs/tickets/Tickets.md`.

## In progress

_(none)_

## Open

| ID | Pri | Area | Title |
|---|---|---|---|
| TLA-0001 | P2 | tests | Integration tests: launch each layout, assert window/pane structure + frames via iTerm2 API read-back |
| TLA-0002 | P2 | backend | Reconcile `wezterm.py`'s own `SPLIT_PLAN` with `layouts.py` (single source of truth) — see [ADR 0007](../decisions/0007-iterm2-backend-and-real-gap-layouts.md) |
| TLA-0003 | P3 | packaging | Ad-hoc sign the py2app bundle to stop TCC/Automation re-prompting after each rebuild |
| TLA-0004 | P3 | ux | Themes: appearance is hardcoded One Dark / Menlo 13; the dynamic profile is fully configurable |
| TLA-0005 | P3 | backend | Cold-start window restoration reopens prior tool windows on relaunch (benign; left alone to avoid closing real work) |

## Blocked

_(none)_

## Done

| ID | Area | Title | Closed |
|---|---|---|---|
| TLA-0006 | docs | Sync docs to the iTerm2 pivot: new [ADR 0007](../decisions/0007-iterm2-backend-and-real-gap-layouts.md), README/concept updates, version bump (commit `79a0aff`) | 2026-07-17 |
