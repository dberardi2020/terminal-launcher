"""Unit tests for composition model: resolve, target expansion, lookup."""
import os
from pathlib import Path

import pytest

from terminal_launcher.model import (
    CompositionError,
    expand_target,
    find_workspace,
    resolve_workspace,
)


CFG = {
    "panes": {
        "code": {"name": "Code", "target": "~/Code", "color": "blue", "model": "opus"},
        "home": {"name": "Home", "target": "~", "color": "green"},
    },
    "settings": {"defaultModel": "opus"},
}


# ---- expand_target ----------------------------------------------------------

def test_expand_target_expands_home():
    assert expand_target("~") == os.path.expanduser("~")


def test_expand_target_expands_env(monkeypatch):
    monkeypatch.setenv("TL_TESTVAR", "/tmp/tl-test")
    assert Path(expand_target("$TL_TESTVAR/x")) == Path("/tmp/tl-test/x")


# ---- find_workspace ---------------------------------------------------------

def test_find_workspace_is_case_and_space_insensitive():
    cfg = {"workspaces": [{"name": "Code"}, {"name": "Home"}]}
    assert find_workspace(cfg, "code")["name"] == "Code"
    assert find_workspace(cfg, "  HOME ")["name"] == "Home"
    assert find_workspace(cfg, "nope") is None


# ---- resolve_workspace ------------------------------------------------------

def test_resolve_fills_and_marks_empty_slots():
    ws = {"name": "W", "layout": "split", "slots": [{"pane": "code"}, None]}
    slots = resolve_workspace(CFG, ws)
    assert len(slots) == 2
    assert not slots[0].empty
    assert slots[0].name == "Code"
    assert slots[0].color == "blue"
    assert slots[0].target == str(Path(os.path.expanduser("~/Code")))
    assert slots[1].empty


def test_resolve_model_precedence_slot_over_pane_over_default():
    # slot override wins
    ws = {"layout": "single", "slots": [{"pane": "code", "model": "haiku"}]}
    assert resolve_workspace(CFG, ws)[0].model == "haiku"
    # pane default when no slot override (code pane declares opus)
    ws = {"layout": "single", "slots": [{"pane": "code"}]}
    assert resolve_workspace(CFG, ws)[0].model == "opus"
    # global default when neither (home pane declares no model)
    ws = {"layout": "single", "slots": [{"pane": "home"}]}
    assert resolve_workspace(CFG, ws)[0].model == "opus"


def test_resolve_pads_missing_slots_as_empty():
    ws = {"layout": "quad", "slots": [{"pane": "code"}]}
    slots = resolve_workspace(CFG, ws)
    assert len(slots) == 4
    assert not slots[0].empty
    assert all(s.empty for s in slots[1:])


def test_resolve_unknown_pane_raises():
    ws = {"layout": "single", "slots": [{"pane": "ghost"}]}
    with pytest.raises(CompositionError):
        resolve_workspace(CFG, ws)


def test_resolve_unknown_layout_raises():
    with pytest.raises(CompositionError):
        resolve_workspace(CFG, {"layout": "bogus", "slots": []})
