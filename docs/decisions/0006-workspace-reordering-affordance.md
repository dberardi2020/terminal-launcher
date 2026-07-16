# 0006 — Workspace reordering affordance

**Status:** Accepted · **Date:** 2026-07-16

## Context

Gallery cards could only be nudged one step with inline `◀ ▶` arrows
(`move_workspace`, ±1). We wanted coarse moves too — jump to front / end — and had
to decide *where* the reordering controls live. The full option set is recorded
here deliberately: this is a reversible UI affordance and the choice may change.

## Options considered

| Option | Shape | Trade-off |
|---|---|---|
| **A. Arrows + Jumps in ⋯ (chosen)** | Keep inline `◀ ▶` for single-step; add **Jump to Front** / **Jump to End** to the existing ⋯ menu | Smallest change; keeps the familiar direct control; adds only the coarse moves that were missing; no new persistent chrome |
| B. Inline `⏮ ◀ ▶ ⏭` | Replace the arrows with four icon buttons per card | One click, fully direct — but four small buttons per card is visually busy |
| C. Arrange row under a full-width Launch | Make Launch full-width; put `⏮ ◀ ▶ ⏭` on their own row beneath it | Always visible, no menu digging — but adds height to every card |
| D. Drag-and-drop via a grip handle | A `⠿` grip; drag a card by the grip to reorder anywhere (grip so drag doesn't fight click-to-load) | Best feel by far — but the most implementation and the most fragile in a wrapping grid |
| E. Nested ⋯ → Arrange → | All four moves inside an "Arrange →" submenu off ⋯ | Tidiest cards — but two clicks and submenu positioning to build |
| F. Flat: all four in ⋯ | Move-to-front / forward / backward / to-end, all in the ⋯ menu, arrows removed | One home for admin actions — but hides the common single-step nudge behind a menu |

## Decision

**Option A.** The inline arrows stay for the frequent single-step nudge (direct
manipulation where it matters); the two coarse "jump" moves join Rename / Duplicate
/ Delete in the ⋯ menu, above a divider. Jump items disable at the edges
(front disabled when already first, end when already last).

Backend: `reorder_workspace(name, position)` where `position ∈ {"front", "end"}`,
alongside the existing `move_workspace(name, direction)` for the arrows.

## Consequences

- Minimal new surface; no layout change to the cards.
- Drag-and-drop (Option D) remains the upgrade path if the menu route feels
  clunky — it's the "make it feel great" option, recorded here so revisiting is a
  status flip, not a re-derivation.
- This record is intentionally exhaustive on options because the affordance is
  expected to be re-evaluated with use.
