"""Config loading, saving, and defaults.

The config is a single JSON file describing panes (reusable terminal identities),
saved workspaces (named compositions), and settings. Both the CLI and the visual
composer read/write this one file — it is the single source of truth.

Resolution order for the config path:
  1. --config <path> / TERMINAL_LAUNCHER_CONFIG env var
  2. ~/.config/terminal-launcher/workspaces.json  (XDG-ish default)
The bundled workspaces.example.json seeds a fresh config on first `init`/`new`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# Named colors map to hex for the composer preview and to Claude Code's /color
# palette for the (optional) in-session color injection.
COLORS = {
    "blue": "#5b8def",
    "orange": "#d1a24f",
    "red": "#e0555f",
    "purple": "#a06bd6",
    "green": "#8a9a4f",
    "cyan": "#4fb3c1",
    "pink": "#d67ba8",
    "gray": "#8a8a9a",
}

# Ordered by capacity — combo (3) sits between split and quad. A "combo" is one
# full-height pane on one side, two stacked on the other (a split ⊕ a quad half).
LAYOUT_CAPACITY = {"single": 1, "split": 2, "combo": 3, "quad": 4}

DEFAULT_CONFIG = {
    "version": 1,
    "settings": {
        "defaultModel": "opus",
        "injectColor": True,
        "colorDelay": 1.5,
    },
    "models": [
        {"id": "claude-fable-5", "label": "Fable 5"},
        {"id": "opus", "label": "Opus 4.8"},
        {"id": "claude-opus-4-7", "label": "Opus 4.7"},
        {"id": "sonnet", "label": "Sonnet 5"},
        {"id": "claude-sonnet-4-6", "label": "Sonnet 4.6"},
        {"id": "haiku", "label": "Haiku 4.5"},
    ],
    "panes": {},
    "workspaces": [],
}


def default_config_path() -> Path:
    env = os.environ.get("TERMINAL_LAUNCHER_CONFIG")
    if env:
        return Path(env).expanduser()
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / "terminal-launcher" / "workspaces.json"


def example_config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "workspaces.example.json"


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    # Fill any missing top-level keys with defaults so callers can rely on shape.
    for key, val in DEFAULT_CONFIG.items():
        data.setdefault(key, json.loads(json.dumps(val)))
    for key, val in DEFAULT_CONFIG["settings"].items():
        data["settings"].setdefault(key, val)
    return data


def save(path: Path, config: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    tmp.replace(path)  # atomic write so a crash never truncates the config


def seed_from_example(path: Path) -> dict:
    """Create a fresh config at `path` from the bundled example."""
    example = example_config_path()
    if example.exists():
        config = load(example)
    else:
        config = json.loads(json.dumps(DEFAULT_CONFIG))
    save(path, config)
    return config


def color_hex(name: str) -> str:
    return COLORS.get(name, "#8a8a9a")
