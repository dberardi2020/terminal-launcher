"""Unit tests for config: colors, capacities, and load/save round-trip."""
from terminal_launcher.config import COLORS, LAYOUT_CAPACITY, color_hex, load, save
from terminal_launcher.layouts import CAPACITY


def test_layout_capacity_agrees_with_layouts_module():
    # The two capacity tables must never drift apart.
    assert LAYOUT_CAPACITY == CAPACITY


def test_color_hex_for_all_known_colors():
    for name in COLORS:
        h = color_hex(name)
        assert h.startswith("#") and len(h) == 7


def test_config_save_load_preserves_data(tmp_path):
    # load() also injects defaults (models, schemaVersion), so we assert our
    # saved data survives the round-trip rather than exact equality.
    path = tmp_path / "workspaces.json"
    cfg = {
        "panes": {"code": {"name": "Code", "target": "~/Code", "color": "blue"}},
        "workspaces": [{"name": "W", "layout": "single", "slots": [{"pane": "code"}]}],
        "settings": {"defaultModel": "opus", "injectColor": True, "colorDelay": 1.5},
    }
    save(path, cfg)
    loaded = load(path)
    assert loaded["panes"] == cfg["panes"]
    assert loaded["workspaces"] == cfg["workspaces"]
    assert loaded["settings"]["defaultModel"] == "opus"
    assert loaded["settings"]["colorDelay"] == 1.5
