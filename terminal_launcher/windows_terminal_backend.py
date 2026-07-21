"""Windows Terminal backend — the Windows terminal layer.

Each filled slot is spawned as its OWN Windows Terminal window and placed at the
slot's screen rectangle (derived from the monitor work area), so a layout is a
set of real, separately-movable OS windows with real desktop gaps for empty
slots — the same model the iTerm2 backend uses on macOS.

Two things make Windows different from the iTerm2 path:

  * No per-pane text API. iTerm2 delivers `/color` with `session.async_send_text`
    (no focus needed). `wt` has no equivalent, so `/color` is injected by focusing
    the target window and pasting the command via the clipboard (see `_inject_color`).
  * Placement is done by the app itself (`SetWindowPos`), compensating for the
    DWM invisible border and per-monitor DPI — not by driving the OS snap UI.
    Neither Windows nor macOS exposes a way to *invoke* native snapping
    programmatically without synthetic input; self-placement gives identical
    alignment deterministically and needs no special permission.

Everything Win32 is pure `ctypes` (no pywin32 dependency). `import`ing this module
is safe on any platform — `ctypes.windll` is only touched inside functions, all of
which are gated behind `available()` (Windows-only).

Interface: available(), describe(), launch() — the shared backend contract.
"""
from __future__ import annotations

import ctypes
import platform
import shutil
import subprocess
import time
from ctypes import wintypes
from pathlib import Path

from . import diag
from .model import ResolvedSlot

_log = diag.get_logger()

# Windows Terminal's top-level window class — how we recognize its windows.
_WT_CLASS = "CASCADIA_HOSTING_WINDOW_CLASS"
_FLIPPABLE = {"split", "combo"}


# ---- availability -----------------------------------------------------------

def available() -> bool:
    return platform.system() == "Windows" and shutil.which("wt") is not None


# ---- Win32 prototypes (configured once, correct 64-bit arg/restypes) ---------

_configured = False


def _configure() -> None:
    """Set arg/restypes so 64-bit HWNDs aren't truncated to 32-bit ints.

    Without this, ctypes defaults every arg to c_int and silently truncates
    window handles on 64-bit Windows — the classic source of "wrong window"
    bugs. Idempotent."""
    global _configured
    if _configured:
        return
    u = ctypes.windll.user32
    u.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                               ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    u.SetWindowPos.restype = wintypes.BOOL
    u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    u.GetWindowRect.restype = wintypes.BOOL
    u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    u.IsWindowVisible.argtypes = [wintypes.HWND]
    u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    u.SetForegroundWindow.argtypes = [wintypes.HWND]
    u.BringWindowToTop.argtypes = [wintypes.HWND]
    u.GetForegroundWindow.restype = wintypes.HWND
    u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    u.GetWindowThreadProcessId.restype = wintypes.DWORD
    u.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    d = ctypes.windll.dwmapi
    d.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD,
                                        ctypes.c_void_p, wintypes.DWORD]
    d.DwmGetWindowAttribute.restype = ctypes.c_long  # HRESULT
    # Clipboard + global memory + mutex — handle args/returns MUST be pointer-wide
    # (HANDLE / HGLOBAL / LPVOID) or 64-bit handles truncate.
    u.OpenClipboard.argtypes = [wintypes.HWND]
    u.GetClipboardData.argtypes = [wintypes.UINT]
    u.GetClipboardData.restype = wintypes.HANDLE
    u.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    u.SetClipboardData.restype = wintypes.HANDLE
    k = ctypes.windll.kernel32
    k.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    k.GlobalAlloc.restype = wintypes.HGLOBAL
    k.GlobalLock.argtypes = [wintypes.HGLOBAL]
    k.GlobalLock.restype = wintypes.LPVOID
    k.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    k.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    k.CreateMutexW.restype = wintypes.HANDLE
    k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k.ReleaseMutex.argtypes = [wintypes.HANDLE]
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    _configured = True


def _set_dpi_aware() -> None:
    """Per-monitor-DPI-aware so work-area coords and SetWindowPos are physical px."""
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


# ---- geometry ---------------------------------------------------------------

def _work_area() -> tuple[int, int, int, int]:
    """Primary-monitor work area (x, y, w, h) in physical px, minus the taskbar."""
    rect = wintypes.RECT()
    SPI_GETWORKAREA = 0x0030
    ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def _slot_rects(layout: str, flip: bool = False) -> list[tuple[int, int, int, int]]:
    """Per-slot rectangles (x, y, w, h) in Win32 screen coords (origin top-left).

    Slot order matches the iTerm2 backend's `_slot_rects` (a deliberate parallel;
    a shared fraction table is a later DRY refactor). A full quad is four windows
    in the four quadrants; empty slots are simply not spawned, leaving real gaps."""
    L, T, W, H = _work_area()
    hw, hh = W // 2, H // 2
    base = {
        "single": [(L, T, W, H)],
        "split": [(L, T, hw, H), (L + hw, T, hw, H)],
        "combo": [(L, T, hw, H), (L + hw, T, hw, hh), (L + hw, T + hh, hw, hh)],
        "quad": [(L, T, hw, hh), (L + hw, T, hw, hh),
                 (L, T + hh, hw, hh), (L + hw, T + hh, hw, hh)],
    }.get(layout, [(L, T, W, H)])
    if flip and layout in _FLIPPABLE:
        base = [(L + (W - (x - L) - rw), y, rw, rh) for (x, y, rw, rh) in base]  # mirror x
    return base


# ---- window discovery -------------------------------------------------------

def _wt_windows() -> set[int]:
    """HWNDs of all visible Windows Terminal top-level windows."""
    u = ctypes.windll.user32
    # WINFUNCTYPE is a Windows-only ctypes attribute — build the callback type
    # here (a Windows-only path), never at import, so this module still imports on
    # macOS (where backend.py imports it).
    enumproc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    found: set[int] = set()

    def cb(hwnd, _lparam):
        if u.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(64)
            u.GetClassNameW(hwnd, buf, 64)
            if buf.value == _WT_CLASS:
                found.add(int(hwnd))
        return True

    u.EnumWindows(enumproc(cb), 0)
    return found


def _spawn_and_find(cmd: list[str], timeout: float = 20.0) -> int | None:
    """Spawn `cmd` and return the HWND of the WT window that appears because of it.

    `wt` returns immediately after handing off to a WindowsTerminal host process
    (new or existing), so we diff the set of WT windows rather than track a PID."""
    before = _wt_windows()
    subprocess.Popen(cmd)
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.4)
        new = _wt_windows() - before
        if new:
            return next(iter(new))
    return None


def _window_title(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


def _wait_title(hwnd: int, name: str, cap: float = 20.0) -> None:
    """Wait until the window title carries the pane name (claude set it via -n).

    This is the readiness gate: snapping/pasting before Claude has painted risks a
    corrupted layout or a dropped command."""
    deadline = time.time() + cap
    while time.time() < deadline:
        if name.lower() in _window_title(hwnd).lower():
            return
        time.sleep(0.3)


# ---- placement --------------------------------------------------------------

def _place(hwnd: int, x: int, y: int, w: int, h: int) -> None:
    """Move+size a window so its VISIBLE frame fills (x, y, w, h).

    Two passes: place the window rect, then correct for the DWM invisible resize
    border (Win11 windows extend a few px beyond their painted frame) so adjacent
    panes meet cleanly with no seam gap."""
    u = ctypes.windll.user32
    SW_RESTORE = 9
    SWP_NOZORDER = 0x0004
    SWP_NOACTIVATE = 0x0010
    flags = SWP_NOZORDER | SWP_NOACTIVATE
    u.ShowWindow(hwnd, SW_RESTORE)  # SetWindowPos can't move a maximized window
    u.SetWindowPos(hwnd, 0, x, y, w, h, flags)

    gr, fr = wintypes.RECT(), wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(gr))
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    hr = ctypes.windll.dwmapi.DwmGetWindowAttribute(
        hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(fr), ctypes.sizeof(fr))
    if hr == 0:
        dl, dt = fr.left - gr.left, fr.top - gr.top
        dr, db = gr.right - fr.right, gr.bottom - fr.bottom
        if any((dl, dt, dr, db)):
            u.SetWindowPos(hwnd, 0, x - dl, y - dt, w + dl + dr, h + dt + db, flags)


# ---- foreground + keyboard injection ----------------------------------------

def _force_foreground(hwnd: int, tries: int = 20) -> bool:
    """Reliably bring `hwnd` to the foreground (bare SetForegroundWindow is flaky).

    Attaches to the current foreground thread's input queue so Windows lets us
    steal focus, then verifies it actually took before returning."""
    u = ctypes.windll.user32
    k = ctypes.windll.kernel32
    target = int(hwnd)
    for _ in range(tries):
        fg = u.GetForegroundWindow()
        fg_tid = u.GetWindowThreadProcessId(fg, None)
        my_tid = k.GetCurrentThreadId()
        u.AttachThreadInput(my_tid, fg_tid, True)
        u.BringWindowToTop(hwnd)
        u.SetForegroundWindow(hwnd)
        u.AttachThreadInput(my_tid, fg_tid, False)
        time.sleep(0.12)
        if int(u.GetForegroundWindow()) == target:
            return True
    return False


# SendInput plumbing.
class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


_INPUT_KEYBOARD = 1
_KEYEVENTF_KEYUP = 0x0002
_VK_RETURN = 0x0D
_VK_CONTROL = 0x11
_VK_V = 0x56

_CF_UNICODETEXT = 13
_GMEM_MOVEABLE = 0x0002


def _send(inputs: list[_INPUT]) -> None:
    n = len(inputs)
    arr = (_INPUT * n)(*inputs)
    ctypes.windll.user32.SendInput(n, arr, ctypes.sizeof(_INPUT))


def _vkey(vk: int, up: bool) -> _INPUT:
    ki = _KEYBDINPUT(wVk=vk, wScan=0, dwFlags=(_KEYEVENTF_KEYUP if up else 0),
                     time=0, dwExtraInfo=None)
    return _INPUT(type=_INPUT_KEYBOARD, u=_INPUTUNION(ki=ki))


# ---- clipboard (pure ctypes; text save/restore) -----------------------------

def _clip_get() -> str | None:
    """Current clipboard text, or None if empty / non-text / unavailable."""
    u = ctypes.windll.user32
    k = ctypes.windll.kernel32
    if not u.OpenClipboard(None):
        return None
    try:
        h = u.GetClipboardData(_CF_UNICODETEXT)
        if not h:
            return None
        p = k.GlobalLock(h)
        if not p:
            return None
        try:
            return ctypes.c_wchar_p(p).value
        finally:
            k.GlobalUnlock(h)
    finally:
        u.CloseClipboard()


def _clip_set(text: str) -> bool:
    """Replace the clipboard with `text` (CF_UNICODETEXT)."""
    u = ctypes.windll.user32
    k = ctypes.windll.kernel32
    if not u.OpenClipboard(None):
        return False
    try:
        u.EmptyClipboard()
        buf = ctypes.create_unicode_buffer(text)   # NUL-terminated
        size = ctypes.sizeof(buf)
        h = k.GlobalAlloc(_GMEM_MOVEABLE, size)
        if not h:
            return False
        p = k.GlobalLock(h)
        ctypes.memmove(p, buf, size)
        k.GlobalUnlock(h)
        u.SetClipboardData(_CF_UNICODETEXT, h)      # ownership passes to the clipboard
        return True
    finally:
        u.CloseClipboard()


# ---- cross-process serialization (a named mutex) ----------------------------

def _acquire_lock(timeout_ms: int = 15000):
    """Take a named mutex so concurrent launches don't clobber each other's clipboard
    or foreground during injection. Returns the handle (release with _release_lock)."""
    k = ctypes.windll.kernel32
    h = k.CreateMutexW(None, False, "TerminalLauncher.ColorInjection")
    if not h:
        return None
    k.WaitForSingleObject(h, timeout_ms)
    return h


def _release_lock(h) -> None:
    if h:
        k = ctypes.windll.kernel32
        k.ReleaseMutex(h)
        k.CloseHandle(h)


# ---- /color injection -------------------------------------------------------

def _paste_and_enter() -> None:
    """Ctrl+V, then a SEPARATE Enter.

    Paste delivers the whole command in one input event, so Claude's slash-command
    autocomplete can't intercept a keystroke and corrupt it. Enter is sent separately —
    a combined text+CR types but does not submit in Claude's TUI."""
    _send([_vkey(_VK_CONTROL, False), _vkey(_VK_V, False),
           _vkey(_VK_V, True), _vkey(_VK_CONTROL, True)])
    time.sleep(0.15)
    _send([_vkey(_VK_RETURN, False), _vkey(_VK_RETURN, True)])


def _inject_color(hwnd: int, color: str) -> None:
    """Focus the window and paste `/color <name>` + Enter.

    Clipboard paste, not per-character typing: the whole command lands atomically, so
    autocomplete can't split it — far fewer synthetic input events than typing each
    letter. The clipboard is saved and restored around the paste, and a named mutex
    serializes the save/set/paste/restore so concurrent launches can't clobber each
    other."""
    lock = _acquire_lock()
    try:
        saved = _clip_get()
        if not _clip_set(f"/color {color}"):
            _log.warning("could not set clipboard for /color '%s'; skipping", color)
            return
        time.sleep(0.1)
        if not _force_foreground(hwnd):
            _log.warning("could not foreground window for /color '%s'; skipping", color)
            return
        _paste_and_enter()
        time.sleep(0.1)
        if saved is not None:
            _clip_set(saved)   # restore the user's clipboard
    finally:
        _release_lock(lock)


# ---- command building -------------------------------------------------------

def _claude() -> str:
    return shutil.which("claude") or "claude"


def _wt_command(slot: ResolvedSlot) -> list[str]:
    """`wt -w new` command that opens ONE new window running this slot's claude.

    `-w new` forces a separate window (not a tab); `--title` tags it; everything
    after the executable is passed to claude verbatim.

    No `--tabColor`: tinting the wt tab from the pane's hex didn't read well against
    Windows Terminal's own theming, so it's dropped for now (revisit with a palette
    tuned for wt). The pane's colour still lands where it matters — Claude's prompt
    bar, via `/color`."""
    return ["wt", "-w", "new", "-d", slot.target,
            "--title", slot.name,
            _claude(), "-n", slot.name, "--model", slot.model]


# ---- describe (dry-run) -----------------------------------------------------

def describe(layout: str, slots: list[ResolvedSlot], flip: bool = False) -> list[str]:
    """Human-readable plan for --dry-run. Uniform separate-window model."""
    rects = _slot_rects(layout, flip) if available() else None
    lines: list[str] = []
    for slot in slots:
        if slot.empty:
            lines.append(f"slot {slot.index + 1}: (empty — desktop gap)")
        else:
            reg = f" @ {rects[slot.index]}" if rects else ""
            lines.append(f"window{reg}  cwd={slot.target}  "
                         f"claude -n '{slot.name}' --model {slot.model}")
    for slot in slots:
        if not slot.empty:
            lines.append(f"color  slot {slot.index + 1} -> '{slot.name}'"
                         f"   /color {slot.color}")
    return lines


# ---- launch -----------------------------------------------------------------

def launch(layout: str, slots: list[ResolvedSlot], inject_color: bool = False,
           workspace_name: str = "workspace", color_delay: float = 1.5,
           flip: bool = False) -> None:
    if not available():
        raise RuntimeError(
            "Windows Terminal (wt) not found on PATH. Install it: "
            "winget install Microsoft.WindowsTerminal")
    _configure()
    _set_dpi_aware()

    filled = [s for s in slots if not s.empty]
    if not filled:
        return
    _log.info("wt launch: layout=%s flip=%s slots=%d filled=%d",
              layout, flip, len(slots), len(filled))
    rects = _slot_rects(layout, flip)

    placed: list[tuple[ResolvedSlot, int]] = []
    for slot in slots:
        if slot.empty:
            continue
        hwnd = _spawn_and_find(_wt_command(slot))
        if not hwnd:
            _log.warning("could not locate wt window for '%s'", slot.name)
            continue
        _wait_title(hwnd, slot.name)  # let claude paint before we resize it
        x, y, w, h = rects[slot.index]
        try:
            _place(hwnd, x, y, w, h)
        except Exception as e:
            _log.warning("placement failed for '%s': %s", slot.name, e)
        placed.append((slot, hwnd))

    if inject_color:
        time.sleep(color_delay)
        for slot, hwnd in placed:
            _wait_title(hwnd, slot.name)
            _inject_color(hwnd, slot.color)
    _log.info("wt launch: built %d filled", len(placed))
