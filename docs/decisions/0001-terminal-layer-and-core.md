# 0001 — Terminal layer: WezTerm + a thin Python core

**Status:** Accepted · **Date:** 2026-07-10

> **Amended by [ADR 0007](0007-iterm2-backend-and-real-gap-layouts.md) (2026-07-16):**
> on **macOS** the terminal layer is now **iTerm2**, not WezTerm — WezTerm could not
> give reliable multi-window control on macOS (`--class` is X11/Wayland-only). WezTerm
> remains the backend everywhere else. The thin-core / swappable-backend design
> recorded here is unchanged — it is exactly what let the macOS layer be a single new
> module.

## Context

The single load-bearing question behind the whole tool: **how does "compose an
arrangement of terminals and launch them" actually work?** Answering it splits into two
independent decisions — the **terminal layer** (what spawns and arranges terminals) and
the **UI toolkit** (what the composer is written in). This ADR records the terminal
layer; the UI is [ADR 0003](0003-visual-composer-pywebview.md).

The environment at decision time: macOS with `python3` (3.14, Homebrew) and
Terminal.app only — no tmux, iTerm2, or WezTerm preinstalled. A "someday Windows
build" is a stated goal, not aspirational.

## Options considered

**Terminal layer** — real OS windows vs. multiplexer panes, and how scriptable:

| Option | Layout model | Scripted spawn | Cross-platform |
|---|---|---|---|
| **WezTerm** | native splits *or* OS windows | Excellent — `wezterm cli spawn` / `split-pane` / `send-text` return pane-ids | **Yes** (same `wezterm cli` on Mac + Windows) |
| tmux | panes in one window | Excellent — `split-window`, `send-keys` | Yes, but single-window feel |
| iTerm2 | native splits + windows | Good — AppleScript / Python API | **Mac-only** |
| kitty | native splits | Good — `kitty @` remote control | Yes |
| Terminal.app | OS windows | Limited — AppleScript, no real splits | **Mac-only**, weakest |

**Core language** — the orchestration layer that reads config, resolves a
workspace, and emits terminal-layer commands. Python was chosen for the *core*
(not the plumbing): already on the Mac, no build step, one codebase for Mac +
Windows, JSON in the stdlib, and it shells out to any terminal layer cleanly.

## Decision

**WezTerm as the terminal layer, driven by a thin Python core.**

An early spike built against Terminal.app (zero-install, real OS windows) but it is
the weakest for programmatic layout and needs a separate, fragile keystroke path per
platform. WezTerm was chosen instead and the
Terminal.app path was dropped.

## Rationale

- **Deterministic scripted layout.** `wezterm cli spawn` / `split-pane` return
  pane-ids, so tiling is exact and repeatable — not a geometry guess.
- **Reliable, native identity.** `send-text --pane-id` delivers text to a
  *specific* pane without focus or Accessibility permissions. That is what makes
  `/color` injection functional rather than a keystroke gamble (see
  [ADR 0002](0002-identity-injection.md)). Tab titles are first-class.
- **Real cross-platform parity.** `wezterm cli` is identical on macOS and Windows,
  so the "someday Windows" build reuses the *same* commands instead of forking into a
  platform-specific split. This is the decisive advantage over the Mac-only options.
- **Thin Python core keeps the plumbing swappable.** The core resolves a workspace
  into platform-agnostic `ResolvedSlot`s; only `wezterm.py` knows about WezTerm. A
  different terminal layer would be one new module.

The layout → split plan the launcher emits:

- `single` → one pane.
- `split` → pane 0, then split pane 0 to the **right**.
- `quad` → pane 0; split **right** of 0; split **below** 0; split **below** 1 → balanced 2×2.

## Consequences

- WezTerm becomes a hard dependency (`brew install --cask wezterm`). Acceptable:
  it is the source of the reliability and portability above.
- The core never manages screen geometry — WezTerm owns tiling. `model.py` carries
  no window-rect math.
- Verified end-to-end on macOS (spawn, tile, name, title, color). Windows is
  unverified but built on the same CLI surface.
- If WezTerm is ever unavailable, the fallback is a *new launcher module* (tmux is
  the most portable candidate), not a rewrite of the core.
- **Revisited by [ADR 0004](0004-heterogeneous-panes-and-window-placement.md):**
  WezTerm's in-terminal tiling cannot hold GUI apps (Chrome, Finder). Supporting
  *heterogeneous* workspaces reintroduces an OS-window placement layer for the
  mixed case — the all-terminal path keeps WezTerm.
- **Amended by [ADR 0007](0007-iterm2-backend-and-real-gap-layouts.md):** the macOS
  terminal layer moved to **iTerm2** — WezTerm's macOS multi-window control was
  unreliable. This ADR still governs the core and the WezTerm (non-macOS) path.
