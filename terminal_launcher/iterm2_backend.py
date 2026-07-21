"""iTerm2 backend — the macOS terminal layer.

Drives iTerm2's Python API. Each launch builds a real GUI window (visible +
maximized) with the tiled layout, runs `claude` per pane in its target dir, sets
titles, and injects `/color` into specific panes — no multiplexer, no
Accessibility. We hold direct Session references to exactly the panes we create,
so targeting is unambiguous (the reliability WezTerm couldn't give us on macOS).

Interface: available(), describe(), launch() — the shared backend contract.
Selection between backends lives in `backend.py`.
"""
from __future__ import annotations

import asyncio
import json
import os
import platform
import shlex
import shutil
import subprocess
import time
from pathlib import Path

from . import diag
from .layouts import FLIPPABLE as _FLIPPABLE
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
    """Human-readable plan for --dry-run.

    Uniform model: every filled slot is its own window at its slot region; empty
    slots are left as bare desktop (real gaps) — for all layouts."""
    def prog(s):
        return f"claude -n '{s.name}' --model {s.model}"

    lines: list[str] = []
    for slot in slots:
        if slot.empty:
            lines.append(f"slot {slot.index + 1}: (empty — desktop gap)")
        else:
            lines.append(f"window @ slot {slot.index + 1} region  "
                         f"cwd={_cwd(slot)}  {prog(slot)}")
    for slot in slots:
        if not slot.empty:
            lines.append(f"color  slot {slot.index + 1} -> '{slot.name}'"
                         f"   /color {slot.color}")
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


def _screen_size() -> tuple[int, int]:
    """Usable main-screen size in points (width, height-below-menubar).

    CoreGraphics via ctypes — permission-free, no AppleScript prompt."""
    try:
        import ctypes

        class CGSize(ctypes.Structure):
            _fields_ = [("width", ctypes.c_double), ("height", ctypes.c_double)]

        class CGPoint(ctypes.Structure):
            _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]

        class CGRect(ctypes.Structure):
            _fields_ = [("origin", CGPoint), ("size", CGSize)]

        cg = ctypes.CDLL(
            "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        cg.CGMainDisplayID.restype = ctypes.c_uint32
        cg.CGDisplayBounds.restype = CGRect
        cg.CGDisplayBounds.argtypes = [ctypes.c_uint32]
        r = cg.CGDisplayBounds(cg.CGMainDisplayID())
        return int(r.size.width), int(r.size.height) - 25  # leave the menu bar
    except Exception as e:
        _log.warning("screen-size probe failed (%s); using fallback", e)
        return 1440, 860


def _slot_rects(layout: str, flip: bool = False) -> list[tuple[int, int, int, int]]:
    """Per-slot screen rectangles (x, y, w, h) in Cocoa coords (origin bottom-left,
    y up) for a layout — used to place filled panes of a PARTIAL layout as
    separate windows, leaving empty slots as bare desktop. Indices match the slot
    order used by the split-plans (see layouts.py)."""
    w, h = _screen_size()
    hw, hh = w // 2, h // 2
    base = {
        "single": [(0, 0, w, h)],
        "split": [(0, 0, hw, h), (hw, 0, hw, h)],
        "combo": [(0, 0, hw, h), (hw, hh, hw, hh), (hw, 0, hw, hh)],
        "quad": [(0, hh, hw, hh), (hw, hh, hw, hh), (0, 0, hw, hh), (hw, 0, hw, hh)],
    }.get(layout, [(0, 0, w, h)])
    if flip and layout in _FLIPPABLE:
        base = [(w - x - rw, y, rw, rh) for (x, y, rw, rh) in base]  # mirror x
    return base


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
    # submit in Claude's TUI.
    try:
        await session.async_send_text(f"/color {color}")
        await asyncio.sleep(0.4)
        await session.async_send_text("\r")
        await asyncio.sleep(0.2)
    except Exception as e:
        _log.warning("color inject failed: %s", e)


def restore_current(color: str, name: str) -> None:
    """Re-inject `/color` + `/rename` into THIS iTerm2 session (the one we're
    running in), identified by `ITERM_SESSION_ID` — addressed to the session
    directly, so no focus or Accessibility permission is needed. Used by the
    `restore` command after Claude Code's `/clear` wipes the pane's identity."""
    import iterm2

    sid = os.environ.get("ITERM_SESSION_ID", "")
    uuid = sid.split(":", 1)[1] if ":" in sid else sid
    failure: list[BaseException] = []

    async def _main(connection):
        # Catch here rather than letting it escape: the iterm2 runner "catches and
        # prints" anything that leaves the coroutine, so a raise would surface as a
        # raw traceback and a bare exit(1) — bypassing cmd_restore's ERROR branch and
        # telling the user nothing useful. Stash it and re-raise on our own terms.
        try:
            app = await iterm2.async_get_app(connection)
            session = app.get_session_by_id(uuid)
            if session is None:
                raise RuntimeError(
                    f"could not resolve this iTerm2 session ({uuid or 'no ITERM_SESSION_ID'}) — "
                    "is this pane running under iTerm2?")
            # text then a lone CR, as separate sends — a single "/cmd x\r" types but
            # doesn't submit in Claude's TUI (same rule as launch-time injection).
            await session.async_send_text(f"/color {color}"); await asyncio.sleep(0.25)
            await session.async_send_text("\r");              await asyncio.sleep(0.15)
            await session.async_send_text(f"/rename {name}"); await asyncio.sleep(0.25)
            await session.async_send_text("\r")
        except Exception as e:  # noqa: BLE001 — re-raised below, outside the runner
            failure.append(e)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        iterm2.run_until_complete(_main, retry=False)  # retry=False: its retry loops forever on auth denial
    except SystemExit as e:  # the lib calls sys.exit() when it can't reach the API
        raise RuntimeError(
            "could not connect to iTerm2's Python API — check that iTerm2 is running "
            "and that Automation permission is granted "
            "(System Settings › Privacy & Security › Automation).") from e
    if failure:
        raise RuntimeError(str(failure[0])) from failure[0]


_SHELL_NAMES = {"-zsh", "zsh", "-bash", "bash", "login", "-fish", "fish", "sh", "-sh"}


async def _close_stray_default_window(connection, keep_ids: set) -> None:
    """When WE cold-started iTerm2 it auto-opens an empty default window; close it.

    Selective on purpose: only a single-pane window running a plain login shell
    is the throwaway. That avoids closing anything the user (or iTerm2 window
    restoration) might have brought back that's actually doing work."""
    import iterm2
    app = await iterm2.async_get_app(connection)
    for w in app.windows:
        if w.window_id in keep_ids:
            continue
        tabs = w.tabs
        if len(tabs) != 1 or len(tabs[0].sessions) != 1:
            continue
        try:
            name = (await tabs[0].sessions[0].async_get_variable("name")) or ""
        except Exception:
            name = ""
        if name.strip().lower() in _SHELL_NAMES:
            try:
                await w.async_close(force=True)
                _log.info("closed stray default window %s", w.window_id[:12])
            except Exception:
                pass


async def _color_pass(inject_color, color_delay, pairs) -> None:
    """Inject /color into each (slot, session) pair, once Claude is ready."""
    if not inject_color:
        return
    await asyncio.sleep(color_delay)  # configured minimum settle
    for slot, s in pairs:
        if not slot.empty:
            await _wait_ready(s)  # then wait until Claude is actually ready
            await _inject_color(s, slot.color)


async def _build(connection, layout, slots, inject_color, color_delay, flip, cold):
    """Each filled slot is its own window at its slot rectangle; empty slots are
    left as bare desktop (real gaps). Uniform across every layout — a full quad is
    four windows in the four quadrants, not one split-pane window."""
    import iterm2
    filled = [s for s in slots if not s.empty]
    if not filled:
        return
    _log.info("iterm2 launch: layout=%s flip=%s slots=%d filled=%d cold=%s",
              layout, flip, len(slots), len(filled), cold)
    rects = _slot_rects(layout, flip)
    pairs, keep = [], set()
    for slot in slots:
        if slot.empty:
            continue
        window = await iterm2.Window.async_create(
            connection, profile=PROFILE_NAME,
            profile_customizations=_profile_overrides(slot))
        window, s0 = await _first_session(connection, window.window_id)
        keep.add(window.window_id)
        try:
            await s0.async_set_name(slot.name)
        except Exception:
            _log.warning("set-name failed for '%s'", slot.name)
        x, y, rw, rh = rects[slot.index]
        try:
            await window.async_set_frame(
                iterm2.Frame(iterm2.Point(x, y), iterm2.Size(rw, rh)))
        except Exception as e:
            _log.warning("slot placement failed: %s", e)
        pairs.append((slot, s0))

    if cold:
        await _close_stray_default_window(connection, keep)
    await _color_pass(inject_color, color_delay, pairs)
    _log.info("iterm2 launch: built %d filled", len(filled))


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
    if _is_running():
        # Already up — connect via the API directly. Do NOT `open` it again:
        # iTerm2 with zero windows pops an empty default window on activation
        # (the "rogue terminal"). Our launch creates the window it needs.
        return
    try:
        subprocess.run(["open", "-g", "-a", "iTerm"], check=False, timeout=10)
    except Exception as e:
        _log.warning("could not pre-launch iTerm2: %s", e)
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
