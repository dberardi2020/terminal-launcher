"""restore — re-apply a launched pane's in-session identity after `/clear`.

Terminal Launcher tags each pane with a name + colour (the Claude session name,
the pane title, and the prompt-bar `/color`). Claude Code's `/clear` — and
reconnecting to a session — resets that *in-session* identity. `restore`
re-detects which pane you are and re-injects `/color` + `/rename`.

The split mirrors the rest of the tool:

  * **Detection is cross-platform** and lives here — match the current directory
    against the panes' `target`s in the config (longest match wins), with a
    per-session sentinel so it still works after you `cd` away.
  * **Injection is platform-specific** and is delegated to the active terminal
    backend via `backend.restore_identity()` — iTerm2 on macOS, Windows Terminal
    on Windows — the same seam `launch` uses.
"""
from __future__ import annotations

import os
from pathlib import Path

from . import backend
from . import config as cfg


def _session_key() -> str:
    """A stable per-terminal-session id for the sentinel filename.

    iTerm2 exposes `ITERM_SESSION_ID` (form `wN:UUID`); Windows Terminal exposes
    `WT_SESSION`. Either lets us remember "which pane this session is" after you
    `cd` off the pane's target directory."""
    sid = os.environ.get("ITERM_SESSION_ID") or os.environ.get("WT_SESSION") or ""
    if ":" in sid:
        sid = sid.split(":", 1)[1]
    return sid or "nosession"


def _sentinel_path(config_path: Path) -> Path:
    return Path(config_path).parent / f".restore-{_session_key()}.txt"


def panes(config: dict) -> list[tuple[str, str, str, str]]:
    """`(id, name, colour, resolved-target)` for each configured pane."""
    out = []
    for pid, p in config.get("panes", {}).items():
        target = os.path.realpath(os.path.expanduser(p.get("target", "~")))
        out.append((pid, p.get("name", pid), p.get("color", "gray"), target))
    return out


def detect(config: dict, config_path: Path, cwd: str | None = None) -> tuple | None:
    """Which pane is this session? Returns `(id, name, colour, target)` or None.

    Matches `cwd` against each pane's target directory — a nested target beats
    its parent (longest match wins). Falls back to a remembered identity in the
    per-session sentinel when `cwd` no longer matches (you `cd`'d away). On a hit,
    (re)writes the sentinel so the identity sticks for the rest of the session.
    """
    here = os.path.realpath(cwd if cwd is not None else os.getcwd())
    best = None
    for row in panes(config):
        target = row[3]
        if here == target or here.startswith(target + os.sep):
            if best is None or len(target) > len(best[3]):
                best = row

    sentinel = _sentinel_path(config_path)
    if best is None and sentinel.exists():
        stored = sentinel.read_text().strip()
        best = next((r for r in panes(config) if r[0] == stored), None)
    if best is not None:
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_text(best[0])
    return best


def restore(config_path: Path, detect_only: bool = False) -> dict:
    """Detect this pane's identity and (unless `detect_only`) re-inject it.

    Returns `{ok: True, name, color, injected}` on a hit, or
    `{ok: False, reason: "unknown", panes: [(name, colour), ...]}` when the cwd
    matches no pane. Injection errors (e.g. no terminal backend, or the current
    session can't be resolved) propagate to the caller."""
    config = cfg.load(config_path)
    hit = detect(config, config_path)
    if hit is None:
        return {"ok": False, "reason": "unknown",
                "panes": [(name, colour) for _, name, colour, _ in panes(config)]}
    _, name, colour, _ = hit
    if not detect_only:
        backend.restore_identity(colour, name)
    return {"ok": True, "name": name, "color": colour, "injected": not detect_only}
