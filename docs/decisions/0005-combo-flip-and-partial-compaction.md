# 0005 — Combo layout, horizontal flip & partial-layout compaction

**Status:** Accepted · **Date:** 2026-07-16

> **Decision 3 amended by [ADR 0007](0007-iterm2-backend-and-real-gap-layouts.md)
> (2026-07-16):** compaction still governs the **WezTerm** path, but the macOS
> **iTerm2** backend now does the opposite — it keeps empty slots as real desktop
> gaps, because iTerm2 gives permission-free window placement (so the Accessibility
> cost that made gaps unattractive below no longer applies). Combo and flip
> (Decisions 1–2) are unaffected.

## Context

Three layout wants surfaced together, and they share one engine (`SPLIT_PLAN` in
`wezterm.py` + `LAYOUT_CAPACITY` in `config.py`), so they're recorded as one ADR:

1. A layout between **split** (2) and **quad** (4): one full-height pane on one
   side, two stacked on the other.
2. A way to **mirror a layout horizontally** — put the "main" pane on the other
   side — saved with the workspace.
3. A fix for **partial layouts** (a workspace with one or more empty slots), which
   today spawn a login-shell pane per empty slot (`_prog` returns `[]` → default
   shell). An empty slot becoming a shell is the actual defect.

## Decision 1 — the `combo` layout (capacity 3)

`LAYOUT_CAPACITY` gains `"combo": 3`, ordered between `split` and `quad`. The split
plan is `[("right", 0), ("bottom", 1)]`: slot 0 opens full-height on the left; slot
1 splits to its right; slot 2 splits below slot 1. Result — a full-height **Main**
on the left, **Top** / **Bottom** stacked on the right. Slot names are
`Main / Top / Bottom` (side-agnostic, so flip doesn't invalidate them).

Name: **Combo** — it's literally a split ⊕ one quad-half. ("Triple", "1+2",
"Main+Stack" were considered; Combo read clearest in the toggle.)

## Decision 2 — horizontal flip (saveable; split & combo only)

A workspace may carry `"flip": true`. Launch mirrors the layout horizontally by
swapping the first *horizontal* split direction (`right`↔`left`); vertical splits
are untouched. So a flipped split puts slot 0 on the right; a flipped combo puts
**Main** on the right with the stack on the left.

- Stored **only when true**, so single/quad configs stay clean. `single`/`quad`
  ignore it (a 2×2 grid has no meaningful horizontal mirror the user asked for).
- The composer shows it live (a `.flip` class reorders the preview columns via
  CSS), and the launched window matches — one boolean drives both.
- Implementation is a *geometry* transform (`_plan(layout, flip)`), not a slot
  reorder: slot identity/model/color are unchanged, only which side each renders on.

## Decision 3 — partial layouts **compact** (they do not switch engines)

The request was "partial layouts should not use WezTerm; tile them instead." Half
right: the shell-pane behaviour is wrong, but switching engines is the wrong fix.

| Option | Empty slot becomes… | Cost | Verdict |
|---|---|---|---|
| **A. Compact (chosen)** | *nothing* — filled panes tile with the layout that fits their count (2→split, 3→combo, 4→quad) | ~15 lines in `model.compact`; no new permission | **Accepted** |
| **B. OS-window tiler** ([ADR 0004](0004-heterogeneous-panes-and-window-placement.md)) | a preserved empty rectangle (gap) | **Accessibility grant** — the exact cost WezTerm was chosen to avoid ([ADR 0001](0001-terminal-layer-and-core.md)) | Rejected for the all-terminal case |
| **C. Keep shells** | a login-shell pane | none | Rejected — this is the bug |

**Why A over B.** WezTerm *cannot* leave a hole — every pane region runs a
program — so "tiled with a gap" is unreachable in the terminal engine regardless.
Reaching for the OS-window placer to draw a gap would drag the Accessibility
permission onto the fleeting launcher for zero benefit on an all-Claude workspace.
Compaction gives the natural outcome (the filled panes fill the window) with no new
cost, and composes with Combo: 3 filled slots of any layout → a combo.

`model.compact(slots)` drops empties, re-indexes the survivors `0..n-1` (so the
split plan lines up), and returns the `COUNT_LAYOUT[n]` layout. A *full* composition
is unchanged (n == capacity resolves back to its own layout). Both the CLI and the
GUI run it right before handing off to `wezterm.launch`, so the two surfaces behave
identically.

**Escape hatch preserved:** if a user genuinely wants empty regions kept as gaps,
that is the one case that still needs Option B — and Option B is exactly what ADR
0004 already scopes (mixed workspaces). This ADR narrows 0004: the OS-window tiler
is now reserved for *heterogeneous* (non-`claude`) workspaces, **not** for partial
all-terminal ones.

## Relationship to ADR 0004

ADR 0004 (OS-window placement for Chrome/Finder panes) stays **Proposed**. This ADR
removes "partial all-terminal layouts" from its motivation: those are handled here,
in-engine, without Accessibility. 0004's remaining job is genuinely mixed panes.

## Consequences

- `combo` is a first-class layout across config, model, launcher, CLI, and GUI.
- `flip` is a per-workspace boolean; forward/back compatible (absent = false).
- Empty slots never launch a shell again; partial compositions reshape to fit.
- The OS-window tiler is now needed *only* for mixed workspaces — a smaller, later
  bet, not a prerequisite for good partial-layout behaviour.
- Not yet built *(under WezTerm)*: the OS-window "preserve the gap" mode.
- **macOS update ([ADR 0007](0007-iterm2-backend-and-real-gap-layouts.md)):** under
  the iTerm2 backend, partial layouts **keep** the empty slots as real desktop gaps
  rather than compacting — the "preserve the gap" mode this ADR deferred, now cheap
  because iTerm2 needs no Accessibility. Compaction remains the WezTerm behaviour.
