"""The composition model: resolve a workspace into concrete panes and geometry.

This is platform-agnostic. It turns a saved workspace (layout + per-slot pane
reference) into a list of `ResolvedSlot`s — each carrying the final target dir,
model, session name, and color — plus the on-screen rectangle it should occupy.
The platform launchers consume this and nothing else.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .config import LAYOUT_CAPACITY, color_hex


@dataclass
class ResolvedSlot:
    index: int
    empty: bool
    pane_id: str | None = None
    name: str = ""
    color: str = ""            # named color, e.g. "blue"
    color_hex: str = "#8a8a9a"
    target: str = ""           # expanded absolute path
    model: str = ""


class CompositionError(Exception):
    pass


def expand_target(raw: str) -> str:
    return str(Path(os.path.expandvars(os.path.expanduser(raw))))


def resolve_workspace(config: dict, workspace: dict) -> list[ResolvedSlot]:
    """Resolve every slot of a workspace against the pane registry + settings."""
    panes = config["panes"]
    default_model = config["settings"].get("defaultModel", "opus")
    layout = workspace.get("layout", "single")
    if layout not in LAYOUT_CAPACITY:
        raise CompositionError(f"Unknown layout '{layout}'")
    cap = LAYOUT_CAPACITY[layout]

    slots_in = list(workspace.get("slots", []))
    resolved: list[ResolvedSlot] = []
    for i in range(cap):
        slot = slots_in[i] if i < len(slots_in) else None
        pane_id = slot.get("pane") if isinstance(slot, dict) else None
        if not pane_id:
            resolved.append(ResolvedSlot(index=i, empty=True))
            continue
        pane = panes.get(pane_id)
        if pane is None:
            raise CompositionError(
                f"Workspace '{workspace.get('name')}' slot {i + 1} references "
                f"unknown pane '{pane_id}'"
            )
        # model precedence: slot override -> pane default -> global default
        model = (slot.get("model") if isinstance(slot, dict) else None) \
            or pane.get("model") or default_model
        color = pane.get("color", "gray")
        resolved.append(ResolvedSlot(
            index=i,
            empty=False,
            pane_id=pane_id,
            name=pane.get("name", pane_id),
            color=color,
            color_hex=color_hex(color),
            target=expand_target(pane.get("target", "~")),
            model=model,
        ))
    return resolved


# A filled-slot count maps to the tightest layout that holds exactly that many
# panes. Partial compositions launch *compacted* to this: empty slots are dropped
# rather than rendered as shells. WezTerm cannot leave a hole — every pane region
# runs a program — so the filled panes expand to fill the window instead. Only
# genuinely mixed (non-Claude) workspaces need the OS-window tiler; see ADR 0004.
COUNT_LAYOUT = {1: "single", 2: "split", 3: "combo", 4: "quad"}


def compact(slots: list[ResolvedSlot]) -> tuple[str, list[ResolvedSlot]]:
    """Drop empty slots; return (effective_layout, filled_slots).

    Re-indexes the kept slots 0..n-1 so the launcher's split plan lines up. A
    *full* composition is unchanged (n == capacity resolves back to its own
    layout — a full quad stays quad, a full combo stays combo)."""
    filled = [s for s in slots if not s.empty]
    for i, s in enumerate(filled):
        s.index = i
    return COUNT_LAYOUT.get(len(filled), "single"), filled


def find_workspace(config: dict, name: str) -> dict | None:
    lname = name.strip().lower()
    for ws in config.get("workspaces", []):
        if ws.get("name", "").lower() == lname:
            return ws
    return None
