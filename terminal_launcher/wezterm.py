"""WezTerm launcher — the terminal layer.

Everything here drives `wezterm cli`, which is identical on macOS and Windows, so
this single module is the launcher for *both* platforms. The only OS-specific bit
is how the GUI is first started (macOS `open`, Windows `wezterm-gui start`).

Why WezTerm: deterministic scripted layout (`spawn`/`split-pane` return pane-ids),
and — the reason identity is reliable here — `send-text --pane-id` delivers text
to a *specific* pane without needing focus or Accessibility permissions. That is
what makes the Claude `/color` + name/title injection functional rather than a
best-effort keystroke gamble (see docs/decisions/0002-identity-injection.md).

Maximized launch (see docs/decisions/0001): a launched workspace opens maximized.
We start a GUI window with our bundled config (`assets/wezterm-maximize.lua`),
whose `gui-startup` handler maximizes the first pane; the remaining panes are then
split INTO that already-maximized window, so the whole tiled layout fills the
screen. `wezterm cli spawn --new-window` has no geometry flag, which is why the
first pane goes through gui-startup instead.

Layout → split plan (slot 0 is the first pane; later slots split off an earlier one):
  single : [P0]
  split  : [P0] + P1 to the right of P0
  combo  : [P0] full-height left; P1 splits right of P0; P2 splits below P1
  quad   : [P0] + P1 right of P0, P2 below P0, P3 below P1  → balanced 2×2

A workspace may set "flip": true to mirror horizontally (split/combo only) — the
first horizontal split direction is swapped (right↔left), so the primary pane
lands on the opposite side. Vertical splits are unaffected.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path

from .model import ResolvedSlot

# (direction, source-slot-index) for each slot after the first.
SPLIT_PLAN: dict[str, list[tuple[str, int]]] = {
    "single": [],
    "split": [("right", 0)],
    "combo": [("right", 0), ("bottom", 1)],
    "quad": [("right", 0), ("bottom", 0), ("bottom", 1)],
}

# Layouts whose horizontal orientation "flip" can mirror.
_FLIPPABLE = {"split", "combo"}
_FLIP_DIR = {"right": "left", "left": "right"}


def _plan(layout: str, flip: bool = False) -> list[tuple[str, int]]:
    """The split plan for a layout, horizontally mirrored when flip is set."""
    plan = SPLIT_PLAN.get(layout, [])
    if flip and layout in _FLIPPABLE:
        plan = [(_FLIP_DIR.get(d, d), src) for d, src in plan]
    return plan

CONFIG_ASSET = Path(__file__).resolve().parent / "assets" / "wezterm-maximize.lua"


def available() -> bool:
    return shutil.which("wezterm") is not None


def _run(args: list[str], capture: bool = True) -> str:
    proc = subprocess.run(args, capture_output=capture, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"{' '.join(args)} failed: {proc.stderr.strip() if capture else ''}")
    return proc.stdout.strip() if capture else ""


# ---- command building (also used for --dry-run) -----------------------------

def _prog(slot: ResolvedSlot) -> list[str]:
    if slot.empty:
        return []  # default shell
    # Resolve claude to an absolute path so WezTerm can exec it regardless of the
    # PATH it inherits — a Dock-launched app hands WezTerm a minimal PATH that omits
    # /opt/homebrew/bin. (empty slots run a login shell, which sources the full PATH.)
    claude = shutil.which("claude") or "claude"
    return ["--", claude, "-n", slot.name, "--model", slot.model]


def _cwd(slot: ResolvedSlot) -> str:
    return slot.target if not slot.empty else str(Path.home())


def describe(layout: str, slots: list[ResolvedSlot], flip: bool = False) -> list[str]:
    """Human-readable plan for --dry-run."""
    plan = _plan(layout, flip)
    lines = []
    first = slots[0]
    lines.append(f"start  --new-window (MAXIMIZED)  cwd={_cwd(first)}  "
                 + (f"claude -n '{first.name}' --model {first.model}"
                    if not first.empty else "(shell)"))
    for i, slot in enumerate(slots[1:], start=1):
        direction, src = plan[i - 1]
        lines.append(f"split  {direction:<6} from slot {src + 1}  cwd={_cwd(slot)}  "
                     + (f"claude -n '{slot.name}' --model {slot.model}"
                        if not slot.empty else "(shell)"))
    for slot in slots:
        if not slot.empty:
            lines.append(f"title  slot {slot.index + 1} -> '{slot.name}'"
                         f"   inject: /color {slot.color}")
    return lines


# ---- GUI lifecycle ----------------------------------------------------------

def _list_panes() -> list[dict]:
    try:
        out = subprocess.run(["wezterm", "cli", "list", "--format", "json"],
                             capture_output=True, text=True)
        return json.loads(out.stdout or "[]")
    except Exception:
        return []


def _start_first_maximized(ws_name: str, first: ResolvedSlot) -> None:
    """Open a NEW maximized GUI window whose sole pane runs the first slot.

    Uses our bundled config so `gui-startup` maximizes the window. The program +
    cwd are passed as the startup command, so gui-startup spawns exactly this
    pane (no throwaway default window)."""
    args = ["start", "--workspace", ws_name, "--cwd", _cwd(first)] + _prog(first)
    env = dict(os.environ, WEZTERM_CONFIG_FILE=str(CONFIG_ASSET))
    if platform.system() == "Windows":
        cmd = ["wezterm-gui"] + args
        subprocess.Popen(cmd, env=env, creationflags=0x00000008)  # DETACHED_PROCESS
    else:
        cmd = ["open", "-na", "WezTerm", "--args"] + args
        subprocess.Popen(cmd, env=env)


def _await_first_pane(ws_name: str, timeout: float = 10.0) -> str:
    """Poll until the workspace's first pane exists; return its pane-id."""
    for _ in range(int(timeout / 0.3)):
        panes = [p for p in _list_panes() if p.get("workspace") == ws_name]
        if panes:
            return str(min(p["pane_id"] for p in panes))
        time.sleep(0.3)
    raise RuntimeError(
        f"WezTerm window for workspace '{ws_name}' did not appear within "
        f"{timeout:.0f}s — is WezTerm installed and able to start?")


# ---- launch -----------------------------------------------------------------

def launch(layout: str, slots: list[ResolvedSlot], inject_color: bool = False,
           workspace_name: str = "workspace", color_delay: float = 1.5,
           flip: bool = False) -> None:
    if not available():
        raise RuntimeError("wezterm not found on PATH. Install it: "
                           "brew install --cask wezterm")

    plan = _plan(layout, flip)
    pane_ids: list[str] = []

    # First pane opens a NEW, MAXIMIZED window (via gui-startup in our config).
    _start_first_maximized(workspace_name, slots[0])
    pane_ids.append(_await_first_pane(workspace_name))

    # Remaining panes split off an earlier pane, INSIDE the maximized window.
    for i, slot in enumerate(slots[1:], start=1):
        direction, src = plan[i - 1]
        split = ["wezterm", "cli", "split-pane",
                 "--pane-id", pane_ids[src], f"--{direction}", "--percent", "50",
                 "--cwd", _cwd(slot)] + _prog(slot)
        pane_ids.append(_run(split))

    # Titles (terminal-side identity) for filled panes.
    for slot, pid in zip(slots, pane_ids):
        if not slot.empty:
            try:
                _run(["wezterm", "cli", "set-tab-title", "--pane-id", pid, slot.name])
            except RuntimeError:
                pass

    # Claude prompt-bar color: inject once sessions have had time to start.
    if inject_color:
        time.sleep(color_delay)
        for slot, pid in zip(slots, pane_ids):
            if slot.empty:
                continue
            _inject_color(pid, slot.color)


def _inject_color(pane_id: str, color: str) -> None:
    """Type `/color <name>` into a pane and submit it.

    The Enter MUST be a separate send-text call: sending "/color x\\r" in one
    shot types the text but does not submit it in Claude's TUI (verified). Two
    calls — text, then a lone carriage return — reliably submit.
    """
    def send(text: str) -> None:
        subprocess.run(
            ["wezterm", "cli", "send-text", "--pane-id", pane_id, "--no-paste", text],
            capture_output=True)

    send(f"/color {color}")
    time.sleep(0.4)
    send("\r")
    time.sleep(0.2)
