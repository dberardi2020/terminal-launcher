"""Diagnostics: a single rotating log file both surfaces (CLI + GUI) write to.

Everything lands in `~/.config/terminal-launcher/terminal-launcher.log` (next to
the config). Python exceptions, launch steps, and — crucially — errors from the
WebView JS (forwarded over the pywebview bridge via `Api.log_client`) all go here,
so a bug in the composer leaves a record instead of vanishing into the WebView
console. `read_tail()` / the `logs` CLI verb / the GUI "Reveal log" button are the
export paths.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import default_config_path

_configured = False


def log_path() -> Path:
    return default_config_path().parent / "terminal-launcher.log"


def get_logger() -> logging.Logger:
    return logging.getLogger("terminal_launcher")


def setup() -> Path:
    """Idempotently attach a file + stderr handler and an uncaught-exception hook."""
    global _configured
    path = log_path()
    if _configured:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = get_logger()
    logger.setLevel(logging.DEBUG)
    fh = RotatingFileHandler(path, maxBytes=512_000, backupCount=2, encoding="utf-8")
    fh.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-5s [%(name)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(fh)
    sh = logging.StreamHandler()  # also to stderr, so background-task output has it too
    sh.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(sh)

    def hook(exc_type, exc, tb):
        logger.error("UNCAUGHT", exc_info=(exc_type, exc, tb))
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = hook
    _configured = True
    logger.info("--- diag ready (log at %s) ---", path)
    return path


def read_tail(n: int = 200) -> str:
    p = log_path()
    if not p.exists():
        return ""
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-n:])
