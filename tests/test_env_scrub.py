"""Tests for the bundled-Python env scrub (`terminal_launcher.backend`).

The py2app bundle sets `PYTHONHOME`/`PYTHONPATH` at its own `Contents/Resources` for its
embedded interpreter. Anything it spawns inherits them — and a cold start launches iTerm2
itself, so every pane does too, making an unrelated `python` in a pane resolve the bundle's
stdlib. What matters is therefore not just that the vars leave `os.environ`, but that
**child processes** stop seeing them; that's what the last test asserts.
"""
import os
import subprocess
import sys

from terminal_launcher import backend


def test_scrub_removes_both_vars(monkeypatch):
    bundle = "/Applications/Terminal Launcher.app/Contents/Resources"
    monkeypatch.setenv("PYTHONHOME", bundle)
    monkeypatch.setenv("PYTHONPATH", bundle)

    backend.scrub_bundled_python_env()

    assert "PYTHONHOME" not in os.environ
    assert "PYTHONPATH" not in os.environ


def test_scrub_is_a_noop_when_unset(monkeypatch):
    monkeypatch.delenv("PYTHONHOME", raising=False)
    monkeypatch.delenv("PYTHONPATH", raising=False)

    backend.scrub_bundled_python_env()  # must not raise

    assert "PYTHONHOME" not in os.environ
    assert "PYTHONPATH" not in os.environ


def test_child_process_does_not_inherit_after_scrub(monkeypatch):
    """The actual point of the fix — what a spawned pane would see.

    Only PYTHONPATH is exercised here: pointing PYTHONHOME at a bogus prefix would stop
    the child interpreter finding its own stdlib, which is the very breakage this guards
    against, but makes for an unrunnable test."""
    monkeypatch.setenv("PYTHONPATH", "/some/bundle/Contents/Resources")

    backend.scrub_bundled_python_env()

    out = subprocess.run(
        [sys.executable, "-c", "import os; print(os.environ.get('PYTHONPATH', '<unset>'))"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert out == "<unset>"


def test_pane_command_scrubs_bundled_python_env():
    """Defence in depth: even if iTerm2 itself is already polluted, the command each
    pane runs is scrubbed, so Claude (and everything it spawns) gets a clean env."""
    from terminal_launcher import iterm2_backend
    from terminal_launcher.model import ResolvedSlot

    slot = ResolvedSlot(index=0, empty=False, pane_id="api", name="API",
                        color="green", color_hex="#8a9a4f", target="/tmp", model="opus")
    cmd = iterm2_backend._command(slot)

    assert cmd.startswith("/usr/bin/env -u PYTHONHOME -u PYTHONPATH ")
    assert "claude" in cmd
    assert "API" in cmd


def test_empty_slot_has_no_command():
    from terminal_launcher import iterm2_backend
    from terminal_launcher.model import ResolvedSlot

    slot = ResolvedSlot(index=1, empty=True, pane_id=None, name="", color="gray",
                        color_hex="#8a8a9a", target="/tmp", model="opus")
    assert iterm2_backend._command(slot) is None
