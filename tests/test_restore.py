"""Tests for restore's cross-platform detection core (terminal_launcher.restore).

Injection is platform-specific and delegated to the backends; detection — which
pane is this session, by cwd — is pure and lives here, so it's what we test.
`detect()` takes an explicit `cwd` so no directory changes are needed."""
from terminal_launcher import restore


def _cfg(panes):
    """panes: {id: (name, color, target)} -> a config dict."""
    return {"panes": {pid: {"name": n, "color": c, "target": t}
                      for pid, (n, c, t) in panes.items()}}


def test_exact_directory_match(tmp_path):
    api = tmp_path / "api"; api.mkdir()
    cfg = _cfg({"api": ("API", "green", str(api))})
    hit = restore.detect(cfg, tmp_path / "workspaces.json", cwd=str(api))
    assert hit is not None
    assert (hit[1], hit[2]) == ("API", "green")


def test_subdirectory_of_target_matches(tmp_path):
    api = tmp_path / "api"; deep = api / "src" / "pkg"; deep.mkdir(parents=True)
    cfg = _cfg({"api": ("API", "green", str(api))})
    hit = restore.detect(cfg, tmp_path / "cfg.json", cwd=str(deep))
    assert hit is not None and hit[1] == "API"


def test_longest_prefix_wins(tmp_path):
    root = tmp_path / "proj"; inner = root / "api"; inner.mkdir(parents=True)
    cfg = _cfg({
        "proj": ("Proj", "blue", str(root)),
        "api":  ("API",  "green", str(inner)),
    })
    hit = restore.detect(cfg, tmp_path / "cfg.json", cwd=str(inner))
    assert hit[1] == "API"  # a nested target beats its parent


def test_sibling_prefix_is_not_a_match(tmp_path):
    # /api must not match /api-v2 just because the string is a prefix
    api = tmp_path / "api"; apiv2 = tmp_path / "api-v2"
    api.mkdir(); apiv2.mkdir()
    cfg = _cfg({"api": ("API", "green", str(api))})
    assert restore.detect(cfg, tmp_path / "cfg.json", cwd=str(apiv2)) is None


def test_no_match_returns_none(tmp_path):
    api = tmp_path / "api"; other = tmp_path / "elsewhere"
    api.mkdir(); other.mkdir()
    cfg = _cfg({"api": ("API", "green", str(api))})
    assert restore.detect(cfg, tmp_path / "cfg.json", cwd=str(other)) is None


def test_sentinel_remembers_identity_after_cd_away(tmp_path, monkeypatch):
    monkeypatch.delenv("ITERM_SESSION_ID", raising=False)
    monkeypatch.delenv("WT_SESSION", raising=False)
    api = tmp_path / "api"; elsewhere = tmp_path / "elsewhere"
    api.mkdir(); elsewhere.mkdir()
    cfgpath = tmp_path / "workspaces.json"
    cfg = _cfg({"api": ("API", "green", str(api))})

    # match in the target dir → writes the per-session sentinel
    assert restore.detect(cfg, cfgpath, cwd=str(api))[1] == "API"
    # cd away → cwd matches nothing, but the sentinel remembers who we are
    hit = restore.detect(cfg, cfgpath, cwd=str(elsewhere))
    assert hit is not None and hit[1] == "API"
