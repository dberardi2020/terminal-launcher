"""iTerm2 backend — the macOS terminal layer.

Drives iTerm2's Python API. Each launch builds a real GUI window (visible +
maximized) with the tiled layout, runs `claude` per pane in its target dir, sets
titles, and injects `/color` into specific panes — no multiplexer, no
Accessibility. We hold direct Session references to exactly the panes we create,
so targeting is unambiguous (the reliability WezTerm couldn't give us on macOS).

Interface mirrors `wezterm.py`: available(), describe(), launch(). Selection
between backends lives in `backend.py`.
"""
from __future__ import annotations

import asyncio
import json
import platform
import shlex
import shutil
import subprocess
import time
from pathlib import Path

from . import diag
from .layouts import plan as _plan
from .model import ResolvedSlot

_log = diag.get_logger()

PROFILE_NAME = "Terminal Launcher"
_PROFILE_GUID = "TL-ITERM2-PROFILE-0001"
_APP = Path("/Applications/iTerm.app")
_DYNAMIC_PROFILES = Path.home() / "Library" / "Application Support" / "iTerm2" / "DynamicProfiles"
_PROFILE_FILE = _DYNAMIC_PROFILES / "terminal-launcher.json"

# One Dark-ish palette — clean default; theming is a later concern.
_ANSI = ["#282c34", "#e06c75", "#98c379", "#e5c07b", "#61afef", "#c678dd",
         "#56b6c2", "#abb2bf", "#545862", "#e06c75", "#98c379", "#e5c07b",
         "#61afef", "#c678dd", "#56b6c2", "#c8ccd4"]
_FONT = "Menlo-Regular 13"


# ---- availability -----------------------------------------------------------

def available() -> bool:
    """iTerm2 is usable: macOS, app installed, and the python lib importable."""
    if platform.system() != "Darwin" or not _APP.exists():
        return False
    try:
        import iterm2  # noqa: F401
    except Exception:
        return False
    return True


# ---- styled profile ---------------------------------------------------------

def _color(hexs: str) -> dict:
    h = hexs.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return {"Red Component": r, "Green Component": g, "Blue Component": b,
            "Color Space": "sRGB", "Alpha Component": 1.0}


def _ensure_profile() -> None:
    """Install/refresh our dynamic profile (iTerm2 hot-reloads this dir)."""
    prof = {
        "Name": PROFILE_NAME,
        "Guid": _PROFILE_GUID,
        "Normal Font": _FONT,
        "Non Ascii Font": _FONT,
        "Horizontal Spacing": 1.0,
        "Vertical Spacing": 1.06,
        "Background Color": _color("#282c34"),
        "Foreground Color": _color("#abb2bf"),
        "Cursor Color": _color("#61afef"),
        "Cursor Text Color": _color("#282c34"),
        "Selection Color": _color("#3e4451"),
        "Selected Text Color": _color("#c8ccd4"),
        "Bold Color": _color("#c8ccd4"),
        "Link Color": _color("#61afef"),
        "Cursor Type": 2,
        "Blinking Cursor": False,
        "Use Bold Font": True,
        "Use Bright Bold": True,
        "ASCII Anti Aliased": True,
        "Non-ASCII Anti Aliased": True,
        "Unlimited Scrollback": True,
        "Columns": 220,
        "Rows": 55,
    }
    for i, hexs in enumerate(_ANSI):
        prof[f"Ansi {i} Color"] = _color(hexs)
    try:
        _DYNAMIC_PROFILES.mkdir(parents=True, exist_ok=True)
        _PROFILE_FILE.write_text(json.dumps({"Profiles": [prof]}, indent=2))
    except OSError as e:
        _log.warning("could not write iTerm2 dynamic profile: %s", e)


# ---- command building (also used for --dry-run) -----------------------------

def _claude() -> str:
    return shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude")


def _command(slot: ResolvedSlot) -> str | None:
    """Custom command for a slot, or None for an empty (default-shell) slot."""
    if slot.empty:
        return None
    parts = [_claude(), "-n", slot.name, "--model", slot.model]
    return " ".join(shlex.quote(p) for p in parts)


def _cwd(slot: ResolvedSlot) -> str:
    return slot.target if not slot.empty else str(Path.home())


def describe(layout: str, slots: list[ResolvedSlot], flip: bool = False) -> list[str]:
    """Human-readable plan for --dry-run."""
    p = _plan(layout, flip)
    lines = [f"window (MAXIMIZED)  cwd={_cwd(slots[0])}  "
             + (f"claude -n '{slots[0].name}' --model {slots[0].model}"
                if not slots[0].empty else "(shell)")]
    for i, slot in enumerate(slots[1:], start=1):
        direction, src = p[i - 1]
        lines.append(f"split  {direction:<6} from slot {src + 1}  cwd={_cwd(slot)}  "
                     + (f"claude -n '{slot.name}' --model {slot.model}"
                        if not slot.empty else "(shell)"))
    for slot in slots:
        if not slot.empty:
            lines.append(f"title  slot {slot.index + 1} -> '{slot.name}'"
                         f"   inject: /color {slot.color}")
    return lines


# ---- iTerm2 async build -----------------------------------------------------

def _profile_overrides(slot: ResolvedSlot):
    import iterm2
    p = iterm2.LocalWriteOnlyProfile()
    cmd = _command(slot)
    if cmd is not None:
        p.set_use_custom_command("Yes")
        p.set_command(cmd)
    p.set_initial_directory_mode(
        iterm2.InitialWorkingDirectory.INITIAL_WORKING_DIRECTORY_CUSTOM)
    p.set_custom_directory(_cwd(slot))
    return p


async def _first_session(connection, window_id: str):
    """Wait out the post-create race: refetch until the window has a session."""
    import iterm2
    for _ in range(40):
        app = await iterm2.async_get_app(connection)
        for w in app.windows:
            if w.window_id == window_id and w.tabs and w.tabs[0].sessions:
                return w, w.tabs[0].sessions[0]
        await asyncio.sleep(0.1)
    raise RuntimeError("iTerm2 window/session did not appear")


def _screen_frame():
    """Visible screen frame (Cocoa, origin bottom-left) for maximize.

    Reads the main display size via CoreGraphics (ctypes) — permission-free, no
    AppleScript/automation prompt. Falls back to a large frame on any failure."""
    import iterm2
    try:
        import ctypes

        class CGPoint(ctypes.Structure):
            _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]

        class CGSize(ctypes.Structure):
            _fields_ = [("width", ctypes.c_double), ("height", ctypes.c_double)]

        class CGRect(ctypes.Structure):
            _fields_ = [("origin", CGPoint), ("size", CGSize)]

        cg = ctypes.CDLL(
            "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        cg.CGMainDisplayID.restype = ctypes.c_uint32
        cg.CGDisplayBounds.restype = CGRect
        cg.CGDisplayBounds.argtypes = [ctypes.c_uint32]
        r = cg.CGDisplayBounds(cg.CGMainDisplayID())
        w, h = int(r.size.width), int(r.size.height)
        menubar = 25  # leave the menu bar visible
        return iterm2.Frame(iterm2.Point(0, 0), iterm2.Size(w, h - menubar))
    except Exception as e:
        _log.warning("screen-size probe failed (%s); using fallback frame", e)
        return iterm2.Frame(iterm2.Point(0, 0), iterm2.Size(1440, 860))


# Substrings that appear once Claude Code's TUI is ready for input. Matching any
# means the `/color` command will land in the prompt rather than be swallowed by
# a still-booting screen. Falls back to a timeout so color still injects if the
# TUI wording ever changes.
_READY_MARKERS = ("shift+tab", "for shortcuts", "auto-accept", "bypass", "auto mode")


async def _wait_ready(session, cap: float = 12.0) -> None:
    """Poll the pane until Claude looks ready for input (or `cap` elapses)."""
    waited = 0.0
    while waited < cap:
        try:
            c = await session.async_get_screen_contents()
            text = " ".join(c.line(i).string for i in range(c.number_of_lines)).lower()
            if any(m in text for m in _READY_MARKERS):
                return
        except Exception:
            pass
        await asyncio.sleep(0.5)
        waited += 0.5


async def _inject_color(session, color: str) -> None:
    # Two calls: text, then a lone CR — a single "/color x\r" types but doesn't
    # submit in Claude's TUI (same finding as the WezTerm backend).
    try:
        await session.async_send_text(f"/color {color}")
        await asyncio.sleep(0.4)
        await session.async_send_text("\r")
        await asyncio.sleep(0.2)
    except Exception as e:
        _log.warning("color inject failed: %s", e)


async def _close_stray_default_window(connection, keep_id: str) -> None:
    """When WE cold-started iTerm2 it auto-opens an empty default window; close it.

    Only invoked on cold start, so every window other than the one we just built
    is that throwaway — safe to close without touching the user's own windows."""
    import iterm2
    app = await iterm2.async_get_app(connection)
    for w in app.windows:
        if w.window_id != keep_id:
            try:
                await w.async_close(force=True)
                _log.info("closed stray default window %s", w.window_id[:12])
            except Exception:
                pass


async def _build(connection, layout, slots, inject_color, color_delay, flip, cold):
    import iterm2
    p = _plan(layout, flip)
    _log.info("iterm2 launch: layout=%s flip=%s panes=%d cold=%s",
              layout, flip, len(slots), cold)

    window = await iterm2.Window.async_create(
        connection, profile=PROFILE_NAME,
        profile_customizations=_profile_overrides(slots[0]))
    window, s0 = await _first_session(connection, window.window_id)
    sessions = [s0]

    if cold:
        await _close_stray_default_window(connection, window.window_id)

    for i, slot in enumerate(slots[1:], start=1):
        direction, src = p[i - 1]
        ns = await sessions[src].async_split_pane(
            vertical=(direction == "right"), profile=PROFILE_NAME,
            profile_customizations=_profile_overrides(slot))
        sessions.append(ns)
        _log.debug("iterm2: split %s from slot %d", direction, src)

    for slot, s in zip(slots, sessions):
        if not slot.empty:
            try:
                await s.async_set_name(slot.name)
            except Exception:
                _log.warning("set-name failed for '%s'", slot.name)

    try:
        await window.async_set_frame(_screen_frame())
    except Exception as e:
        _log.warning("maximize failed: %s", e)

    _log.info("iterm2 launch: built %d panes", len(sessions))

    if inject_color:
        await asyncio.sleep(color_delay)  # configured minimum settle
        for slot, s in zip(slots, sessions):
            if not slot.empty:
                await _wait_ready(s)       # then wait until Claude is actually ready
                await _inject_color(s, slot.color)


# ---- launch (sync entry point) ----------------------------------------------

def _is_running() -> bool:
    try:
        return subprocess.run(["pgrep", "-x", "iTerm2"],
                              capture_output=True).returncode == 0
    except Exception:
        return True  # assume running; worst case we skip the stray-window cleanup


def _ensure_running() -> None:
    """Launch iTerm2 if needed and wait (bounded) until it is up.

    We wait here rather than relying on the API's connect-retry, because that
    retry loops forever on an auth failure — see launch()."""
    if not _APP.exists():
        return
    already = _is_running()
    try:
        subprocess.run(["open", "-g", "-a", "iTerm"], check=False, timeout=10)
    except Exception as e:
        _log.warning("could not pre-launch iTerm2: %s", e)
        return
    if already:
        return
    for _ in range(40):  # up to ~8s for a cold-started iTerm2 to come up
        if _is_running():
            time.sleep(1.5)  # small settle for the API server to bind its socket
            return
        time.sleep(0.2)


def launch(layout: str, slots: list[ResolvedSlot], inject_color: bool = False,
           workspace_name: str = "workspace", color_delay: float = 1.5,
           flip: bool = False) -> None:
    if not available():
        raise RuntimeError(
            "iTerm2 not available. Install it: brew install --cask iterm2")
    import iterm2

    _ensure_profile()
    cold = not _is_running()   # did WE start iTerm2? (affects stray-window cleanup)
    _ensure_running()

    async def main(connection):
        await _build(connection, layout, slots, inject_color, color_delay, flip, cold)

    # Own event loop so this works on a GUI worker thread (no ambient loop there).
    # retry=False: the API's retry loops FOREVER on an auth failure, so we never
    # use it — _ensure_running() already waited for iTerm2 to be up.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        iterm2.run_until_complete(main, retry=False)
    except Exception as e:
        # Most likely cause: iTerm2 API auth (cookie) request was denied — the
        # app needs Automation permission to control iTerm2.
        _log.exception("iTerm2 launch failed")
        raise RuntimeError(
            "Could not control iTerm2. Grant permission at System Settings › "
            "Privacy & Security › Automation › Terminal Launcher › iTerm, then "
            "try again."
        ) from e
    finally:
        try:
            loop.close()
        except Exception:
            pass
