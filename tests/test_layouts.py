"""Unit tests for the shared layout split-plans (terminal-agnostic)."""
from terminal_launcher.layouts import SPLIT_PLAN, CAPACITY, FLIPPABLE, plan


def test_capacity_matches_plan_length():
    for name, p in SPLIT_PLAN.items():
        assert CAPACITY[name] == len(p) + 1


def test_capacities_are_expected():
    assert CAPACITY == {"single": 1, "split": 2, "combo": 3, "quad": 4}


def test_plan_single_is_empty():
    assert plan("single") == []


def test_plan_split():
    assert plan("split") == [("right", 0)]


def test_plan_combo():
    assert plan("combo") == [("right", 0), ("bottom", 1)]


def test_plan_quad():
    assert plan("quad") == [("right", 0), ("bottom", 0), ("bottom", 1)]


def test_flip_split_mirrors_horizontal():
    assert plan("split", flip=True) == [("left", 0)]


def test_flip_combo_mirrors_only_horizontal_split():
    # right -> left; the vertical (bottom) split is untouched
    assert plan("combo", flip=True) == [("left", 0), ("bottom", 1)]


def test_flip_is_noop_for_non_flippable_layouts():
    assert "single" not in FLIPPABLE
    assert "quad" not in FLIPPABLE
    assert plan("single", flip=True) == plan("single")
    assert plan("quad", flip=True) == plan("quad")


def test_unknown_layout_returns_empty_plan():
    assert plan("bogus") == []
