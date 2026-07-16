"""Terminal backend selection.

The app talks to ONE terminal-layer interface — available(), describe(),
launch() — and this module routes to the right implementation per platform:

  macOS   -> iTerm2 (native windows, unambiguous per-pane control, no
             Accessibility); falls back to WezTerm if iTerm2 isn't installed.
  other   -> WezTerm (single cross-platform binary; the Windows path).

Backends are interchangeable because each is a thin driver behind the same three
functions (see wezterm.py / iterm2_backend.py).
"""
from __future__ import annotations

import platform

from . import wezterm
from . import iterm2_backend


def _impl():
    if platform.system() == "Darwin" and iterm2_backend.available():
        return iterm2_backend
    return wezterm


def name() -> str:
    return "iTerm2" if _impl() is iterm2_backend else "WezTerm"


def install_hint() -> str:
    if _impl() is iterm2_backend:
        return "brew install --cask iterm2  (macOS)"
    return ("brew install --cask wezterm  (macOS) / "
            "winget install wez.wezterm  (Windows)")


def available() -> bool:
    return _impl().available()


def describe(layout, slots, flip: bool = False):
    return _impl().describe(layout, slots, flip)


def launch(layout, slots, inject_color: bool = False,
           workspace_name: str = "workspace", color_delay: float = 1.5,
           flip: bool = False) -> None:
    return _impl().launch(layout, slots, inject_color=inject_color,
                          workspace_name=workspace_name,
                          color_delay=color_delay, flip=flip)
