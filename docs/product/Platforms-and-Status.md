# Platforms & Status

## Requirements

- **Python 3.10+** (uses `from __future__ import annotations`; developed on 3.14).
- **Claude Code** (`claude`) on your `PATH` — what each filled pane runs.
- **A terminal backend** — the layer that actually spawns and tiles the panes:

| Platform | Backend | Install |
|---|---|---|
| **macOS** | [iTerm2](https://iterm2.com) | `brew install --cask iterm2` |
| **elsewhere** | [WezTerm](https://wezterm.org) | `winget install wez.wezterm` |

On macOS, WezTerm is also the **fallback** if iTerm2 isn't installed.

## How the two backends differ

Both open your workspace tiled; they differ in *how*, and in how they handle a
**partial** layout (a workspace with an empty slot):

| | Full layout | Partial layout (empty slots) |
|---|---|---|
| **iTerm2 (macOS)** | one maximized split-pane window | one window per filled slot at its true position; **empty slots left as real desktop gaps** |
| **WezTerm (elsewhere)** | one split-pane window | **compacted** — empties dropped, filled panes expand to fill; no desktop gap |

The difference is deliberate: iTerm2 can place windows with no special permission, so it
preserves the true geometry; WezTerm can't leave a hole (every pane region must run a
program), so it compacts. Either way, **an empty slot never launches a blank shell.**

## Permissions

- **macOS / iTerm2** — the first launch prompts **once** for **Automation** permission
  (“Terminal Launcher wants to control iTerm2”). This is how iTerm2's Python API is
  driven. If denied, launching fails with a pointer to **System Settings › Privacy &
  Security › Automation**. Note this is Automation, *not* Accessibility — a lighter,
  one-time consent.
- **Identity injection** (`/color`, session name, title) targets a specific pane
  directly and needs **no** extra permissions.

## Platform status

- **macOS** — **working and verified end-to-end** (spawn, tile, name, title, color) on
  the **iTerm2** backend. This is the actively used and tested path.
- **Windows / other** — **unverified.** The WezTerm backend drives `wezterm cli`, which
  is identical across platforms, so the commands are the same; only the initial GUI
  start differs. Treat it as cross-platform *by construction* and verify before relying
  on it.

## Deferred / not yet built

- **Windows verification** — the WezTerm path has only been run on macOS.
- **Heterogeneous panes** — non-terminal panes (a browser, a file manager) tiled
  alongside Claude terminals. This needs an OS-window placement layer (and, on macOS, an
  Accessibility grant). Direction recorded in
  [ADR 0004](../decisions/0004-heterogeneous-panes-and-window-placement.md); not scheduled.
- **Directory-owned identity** — whether a pane's identity should travel with its repo
  rather than live only in this config. Open question.
- **Dock `.app` packaging** — a double-clickable build of the visual composer via
  py2app exists in [`packaging/`](../../packaging/); an unsigned bundle may re-prompt for
  Automation after each rebuild.

---

*The reasoning behind the backend split lives in
[ADR 0007](../decisions/0007-iterm2-backend-and-real-gap-layouts.md); the original
terminal-layer decision in [ADR 0001](../decisions/0001-terminal-layer-and-core.md).*
