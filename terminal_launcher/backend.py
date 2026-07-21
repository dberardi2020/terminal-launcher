"""Terminal backend selection.

The app talks to ONE terminal-layer interface — available(), describe(),
launch() — and this module routes to the platform's native backend:

  macOS   -> iTerm2           (native windows placed by geometry; no Accessibility)
  Windows -> Windows Terminal (native windows placed by geometry; no permission prompt)

Both realize the same model: one real OS window per pane, placed by geometry,
with real desktop gaps for empty slots. Other platforms have no native backend —
there available() reports False and launch() raises a clear error.

Each backend is a thin driver behind the same three functions (see
iterm2_backend.py / windows_terminal_backend.py). Importing this module is safe on
every platform — the heavy per-OS deps (the `iterm2` lib, `ctypes.windll`) are
touched lazily inside each backend, never at import time.
"""
from __future__ import annotations

from . import iterm2_backend
from . import windows_terminal_backend


def _impl():
    """The active backend module for this platform, or None if there is none."""
    if iterm2_backend.available():
        return iterm2_backend
    if windows_terminal_backend.available():
        return windows_terminal_backend
    return None


def name() -> str:
    impl = _impl()
    if impl is iterm2_backend:
        return "iTerm2"
    if impl is windows_terminal_backend:
        return "Windows Terminal"
    return "none"


def install_hint() -> str:
    return ("brew install --cask iterm2  (macOS) / "
            "winget install Microsoft.WindowsTerminal  (Windows)")


def available() -> bool:
    return _impl() is not None


def describe(layout, slots, flip: bool = False):
    impl = _impl()
    if impl is None:
        return ["(no terminal backend available on this platform)"]
    return impl.describe(layout, slots, flip)


def launch(layout, slots, inject_color: bool = False,
           workspace_name: str = "workspace", color_delay: float = 1.5,
           flip: bool = False) -> None:
    impl = _impl()
    if impl is None:
        raise RuntimeError(
            "No supported terminal backend on this platform. "
            "macOS: install iTerm2. Windows: install Windows Terminal.")
    return impl.launch(layout, slots, inject_color=inject_color,
                       workspace_name=workspace_name,
                       color_delay=color_delay, flip=flip)


def restore_identity(color: str, name: str) -> None:
    """Re-inject `/color` + `/rename` into the CURRENT terminal session.

    The `restore` command uses this to re-apply a pane's identity after Claude
    Code's `/clear` wipes it. Routes to the active backend's `restore_current`,
    mirroring launch()'s per-platform seam (iTerm2 / Windows Terminal)."""
    impl = _impl()
    if impl is None:
        raise RuntimeError(
            "No supported terminal backend on this platform. "
            "macOS: install iTerm2. Windows: install Windows Terminal.")
    impl.restore_current(color, name)
