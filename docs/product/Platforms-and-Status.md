# Platforms & Status

## Requirements

- **Python 3.10+** (uses `from __future__ import annotations`; developed on 3.14).
- **Claude Code** (`claude`) on your `PATH` — what each filled pane runs.
- **A terminal backend** — the layer that actually spawns and tiles the panes:

| Platform | Backend | Install |
|---|---|---|
| **macOS** | [iTerm2](https://iterm2.com) | `brew install --cask iterm2` |
| **Windows** | [Windows Terminal](https://aka.ms/terminal) | `winget install Microsoft.WindowsTerminal` |

Other platforms have no native backend yet; there the launcher reports no terminal and
does nothing.

## How the two backends work

Both realize the **same** model: every filled slot is its own OS window placed at its
position on screen, and an empty slot is left as a **real desktop gap** — for every
layout, on both platforms. A full quad is four windows in the four quadrants; a partial
quad is however-many windows with gaps where the empties are.

| | What a launch does |
|---|---|
| **iTerm2 (macOS)** | a window per filled slot via the iTerm2 API, placed at its rect |
| **Windows Terminal (Windows)** | a `wt` window per filled slot, placed with `SetWindowPos` |

They differ only in the mechanics of spawning and identity injection, never in the
resulting layout. **An empty slot never launches a blank shell** — it's simply not there.

## Permissions

- **macOS / iTerm2** — the first launch prompts **once** for **Automation** permission
  (“Terminal Launcher wants to control iTerm2”). This is how iTerm2's Python API is
  driven. If denied, launching fails with a pointer to **System Settings › Privacy &
  Security › Automation**. Note this is Automation, *not* Accessibility — a lighter,
  one-time consent.
- **Windows / Windows Terminal** — **no permission prompt.** Spawning `wt` windows and
  positioning them needs nothing special.
- **Identity injection** (`/color`, session name, title) targets a specific window/session
  directly. On macOS it needs no extra permission; on Windows it briefly focuses the target
  window to paste the command.

## Platform status

- **macOS** — **working and verified end-to-end** (spawn, tile, name, title, color) on
  the **iTerm2** backend. The actively used, tested path.
- **Windows** — **native Windows Terminal backend, mostly verified.** Geometry, window
  discovery, placement, and DWM-border compensation are live-tested (the visible frame
  lands pixel-exact); the `claude` spawn + `/color` clipboard-paste injection is written to the
  proven pattern and awaits a real-session smoke test. Placement is primary-monitor only
  for now.
- **Other platforms** — no native backend; the launcher reports no terminal.

## Deferred / not yet built

- **Windows `/color` smoke test** — the paste-injection path needs one real launch to
  confirm the command lands cleanly in Claude's TUI. Multi-monitor placement is also not
  yet done (primary monitor only).
- **Heterogeneous panes** — non-terminal panes (a browser, a file manager) tiled
  alongside Claude terminals. This needs a general OS-window placement layer. Direction
  recorded in [ADR 0004](../decisions/0004-heterogeneous-panes-and-window-placement.md); not
  scheduled.
- **Directory-owned identity** — whether a pane's identity should travel with its repo
  rather than live only in this config. Open question.
- **Packaging** — a double-clickable build of the visual composer exists for macOS (py2app,
  in [`packaging/`](../../packaging/)) and Windows (PyInstaller, in
  [`packaging/windows/`](../../packaging/windows/)); an unsigned macOS bundle may re-prompt
  for Automation after each rebuild.

---

*The reasoning behind the uniform one-window-per-pane model and the Windows Terminal
backend lives in [ADR 0008](../decisions/0008-one-window-per-pane-and-windows-terminal-backend.md)
(building on [0007](../decisions/0007-iterm2-backend-and-real-gap-layouts.md) and
[0001](../decisions/0001-terminal-layer-and-core.md)).*
