#!/usr/bin/env python3
"""restore — re-apply a Claude pane's /color and /rename after /clear.

Terminal Launcher tags each launched pane with a name and colour so panes are
distinguishable at a glance. Claude Code's `/clear` (or a reconnect) resets that
in-session identity. This script re-detects the pane's identity from Terminal
Launcher's `panes` registry (matched by cwd, remembered per-session in a
sentinel file) and re-injects it into the current iTerm2 session via the API —
no focus or Accessibility permission needed.

Run with Terminal Launcher's venv python (it has the `iterm2` lib), via
`env -u PYTHONHOME -u PYTHONPATH`. Set TL_RESTORE_DETECT_ONLY=1 to detect the
identity without injecting (used by tests / dry runs).
"""
import os, sys, json, asyncio
from pathlib import Path

CFG = Path.home() / ".config/terminal-launcher/workspaces.json"


def _uuid():
    sid = os.environ.get("ITERM_SESSION_ID", "")
    return sid.split(":", 1)[1] if ":" in sid else sid


def _panes():
    cfg = json.loads(CFG.read_text())
    return [(pid, p.get("name", pid), p.get("color", "gray"),
             os.path.realpath(os.path.expanduser(p.get("target", "~"))))
            for pid, p in cfg.get("panes", {}).items()]


def _sentinel():
    return Path.home() / f".config/terminal-launcher/.restore-{_uuid() or 'nosession'}.txt"


def detect():
    cwd = os.path.realpath(os.getcwd())
    best = None
    for row in _panes():
        tgt = row[3]
        if cwd == tgt or cwd.startswith(tgt + os.sep):
            if best is None or len(tgt) > len(best[3]):
                best = row
    if best is None and _sentinel().exists():                # fall back to remembered identity
        stored = _sentinel().read_text().strip()
        best = next((r for r in _panes() if r[0] == stored), None)
    if best:
        _sentinel().write_text(best[0])
    return best


def inject(color, name):
    import iterm2

    async def main(conn):
        app = await iterm2.async_get_app(conn)
        sess = app.get_session_by_id(_uuid())
        if sess is None:
            raise RuntimeError(f"could not resolve current iTerm2 session {_uuid()!r}")
        # text then a lone CR, as separate sends — one combined send never submits
        await sess.async_send_text(f"/color {color}"); await asyncio.sleep(0.25)  # let text register before submit
        await sess.async_send_text("\r");               await asyncio.sleep(0.15)
        await sess.async_send_text(f"/rename {name}");  await asyncio.sleep(0.25)
        await sess.async_send_text("\r")

    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    iterm2.run_until_complete(main, retry=False)             # retry=False: its retry loops forever on auth denial


def main():
    hit = detect()
    if not hit:
        print("UNKNOWN\t" + "\t".join(f"{n}={c}" for _, n, c, _ in _panes()))
        return 2
    _, name, color, _ = hit
    print(f"DETECTED\t{name}\t{color}")
    if os.environ.get("TL_RESTORE_DETECT_ONLY") != "1":
        inject(color, name)
        print(f"RESTORED\t/color {color}  +  /rename {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
