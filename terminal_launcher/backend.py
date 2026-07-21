"""Terminal backend selection.

The app talks to ONE terminal-layer interface — available(), describe(),
launch() — and this module routes to the platform's native backend:

  macOS -> iTerm2 (native windows placed by geometry; no Accessibility).

Other platforms have no native backend yet (a Windows Terminal backend is
planned); there, available() reports False and launch() raises a clear error.
Each backend is a thin driver behind the same three functions (see
iterm2_backend.py). Importing this module is safe on every platform — the heavy
per-OS deps (e.g. the `iterm2` lib) are imported lazily inside each backend.
"""
from __future__ import annotations

from . import iterm2_backend


def _impl():
    """The active backend module for this platform, or None if there is none."""
    if iterm2_backend.available():
        return iterm2_backend
    return None


def name() -> str:
    return "iTerm2" if _impl() is not None else "none"


def install_hint() -> str:
    return "brew install --cask iterm2  (macOS)"


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
            "macOS: install iTerm2 (brew install --cask iterm2).")
    return impl.launch(layout, slots, inject_color=inject_color,
                       workspace_name=workspace_name,
                       color_delay=color_delay, flip=flip)
