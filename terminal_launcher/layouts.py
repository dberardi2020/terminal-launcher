"""Layout split-plans — shared by every terminal backend.

A plan is a list of (direction, source-slot-index) for each slot AFTER the first:
slot 0 is the first pane; each later slot splits off an already-created pane.

  single : [P0]
  split  : [P0] | P1 to the right of P0
  combo  : [P0] full-height left; P1 right of P0; P2 below P1  (1 full + 2 stacked)
  quad   : [P0] + P1 right of P0, P2 below P0, P3 below P1     (balanced 2x2)

A layout may be horizontally mirrored ("flip") for split/combo: the first
horizontal split direction is swapped (right<->left) so the primary pane lands on
the opposite side. Vertical splits are unaffected.
"""
from __future__ import annotations

SPLIT_PLAN: dict[str, list[tuple[str, int]]] = {
    "single": [],
    "split": [("right", 0)],
    "combo": [("right", 0), ("bottom", 1)],
    "quad": [("right", 0), ("bottom", 0), ("bottom", 1)],
}

# How many panes each layout holds.
CAPACITY = {name: len(plan) + 1 for name, plan in SPLIT_PLAN.items()}

# Layouts whose horizontal orientation "flip" can mirror.
FLIPPABLE = {"split", "combo"}
_FLIP_DIR = {"right": "left", "left": "right"}


def plan(layout: str, flip: bool = False) -> list[tuple[str, int]]:
    """The split plan for a layout, horizontally mirrored when flip is set."""
    p = SPLIT_PLAN.get(layout, [])
    if flip and layout in FLIPPABLE:
        p = [(_FLIP_DIR.get(d, d), src) for d, src in p]
    return p
