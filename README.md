# Terminal Launcher

**Compose and launch tiled Claude Code sessions with one command.**

[![Tests](https://github.com/dberardi2020/terminal-launcher/actions/workflows/tests.yml/badge.svg)](https://github.com/dberardi2020/terminal-launcher/actions/workflows/tests.yml)
![platform: macOS | Windows](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue)
![python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![license: MIT](https://img.shields.io/badge/license-MIT-green)

You often want several Claude Code sessions open at once — each pointed at a different
part of your work, laid out side by side so you can see them together. Terminal Launcher
lets you define those terminals once as reusable **panes**, arrange them into a
**layout**, save the arrangement as a **workspace**, and launch the whole set — tiled,
named, and color-tagged — with a single command (native iTerm2 windows on macOS, Windows
Terminal windows on Windows).

![The Terminal Launcher visual composer](docs/assets/composer.png)

## Model, in three words

- **Pane** — a terminal identity: `name · color · target dir · model`. Reusable.
- **Layout** — the shape: `single` (1), `split` (2 side-by-side), `combo` (3 — one full
  pane + two stacked), `quad` (2×2). `split` and `combo` can be **flipped** horizontally
  (saved per workspace). Leave slots empty and those positions are left as **real desktop
  gaps** on launch — every filled slot is its own window at its true position; empties
  never launch a shell.
- **Workspace** — a saved composition: a layout with a pane assigned to each slot.

Panes and workspaces are *data* (your config); the composer and launcher are the product.
Ship any pane set you like.

## Requirements

- **Python 3.10+** (uses `from __future__ import annotations`; developed on 3.14).
- **A terminal backend** — the layer that spawns and tiles the panes:
  - **macOS → [iTerm2](https://iterm2.com)** (`brew install --cask iterm2`). Its Python
    API drives native windows; the first launch prompts once for Automation permission to
    control iTerm2.
  - **Windows → [Windows Terminal](https://aka.ms/terminal)**
    (`winget install Microsoft.WindowsTerminal`). Ships with Windows 11; spawned and
    placed via Win32 with no permission prompt.
- **Claude Code** (`claude`) on your `PATH` — what each filled pane runs.

## Install

No build step. On macOS/Linux, symlink the entry point onto your `PATH`:

```sh
git clone https://github.com/dberardi2020/terminal-launcher.git
cd terminal-launcher
ln -s "$(pwd)/bin/terminal-launcher" ~/.local/bin/terminal-launcher
```

On Windows, run it as a module (`py -m terminal_launcher …`) from the repo, or use the
`terminal-launcher.cmd` shim in [`packaging/windows/`](packaging/windows/).

Then seed a config and compose your first workspace (substitute `py -m terminal_launcher`
on Windows):

```sh
terminal-launcher init        # seed ~/.config/terminal-launcher/workspaces.json
terminal-launcher new         # interactively compose + save a workspace
terminal-launcher launch Docs # tile it up
```

### Hand it to your coding agent

Already inside Claude Code (or Cursor, or any coding agent)? Paste this and it will do
the install for you:

```text
Install Terminal Launcher for my platform from
https://github.com/dberardi2020/terminal-launcher

- Clone the repo (or use it in place if it's already on disk).
- macOS/Linux: symlink the entry point onto my PATH, e.g.
  `ln -s "$(pwd)/bin/terminal-launcher" ~/.local/bin/terminal-launcher`.
- Windows: it runs as a module — `py -m terminal_launcher`.
- Then run `terminal-launcher init` to seed my config, and walk me through
  `terminal-launcher new` to compose my first workspace.

It needs Python 3.10+, Claude Code (`claude`) on my PATH, and a terminal backend:
iTerm2 on macOS (`brew install --cask iterm2`) or Windows Terminal on Windows
(`winget install Microsoft.WindowsTerminal`). Tell me if anything is missing.
```

### Double-clickable app (optional)

You can also build a Dock/Start-Menu app for the visual composer — **macOS** via py2app,
**Windows** via PyInstaller (or a no-build Start Menu shortcut). See
[`packaging/README.md`](packaging/README.md); on macOS it's one command:
`./packaging/install-macos.sh`.

## Commands

| Verb | What it does |
|---|---|
| `list` | List saved workspaces. |
| `panes` | List configured panes. |
| `preview <name>` | Text preview of a workspace's layout. |
| `launch <name>` | Launch a workspace. `--dry-run` prints the plan; `--inject-color` types `/color` into each session. |
| `new` | Interactively compose a **new** workspace and save it. |
| `edit <name>` | Interactively edit an existing workspace. |
| `delete <name>` | Remove a workspace. |
| `pane-new` | Interactively add a new pane (terminal identity). |
| `gui` | Open the visual composer — a native window (launchpad + click-a-cell editor + pane management). |
| `init` | Create a starter config from the bundled example. |

The interactive `new` / `edit` / `pane-new` verbs **write back to the config** — the CLI
and the visual composer edit the same file and never diverge.

## Configuration

One JSON file is the single source of truth for panes, workspaces, and settings.
Resolution order:

1. `--config <path>` or `TERMINAL_LAUNCHER_CONFIG`
2. `$XDG_CONFIG_HOME/terminal-launcher/workspaces.json`
3. `~/.config/terminal-launcher/workspaces.json`

See [`workspaces.example.json`](workspaces.example.json) for the shape. Model precedence
when launching a slot: **slot override → pane default → global default**.

## Identity in-session

A launched pane carries its identity three ways: the Claude **session name**
(`claude -n <name>`), the **pane title** (the iTerm2 session name on macOS, or the `wt`
tab title on Windows), and — optionally — the Claude prompt-bar **color** (`/color <name>`,
injected with `--inject-color` or `settings.injectColor`). On macOS injection targets the
session directly (no Accessibility permission); on Windows it briefly focuses the window to
paste the command.

## Platform status

- **macOS** — working and verified end-to-end (spawn, tile, name, title, color) on the
  **iTerm2** backend.
- **Windows** — native **Windows Terminal** backend; geometry, window discovery, and
  placement are live-verified, and the `/color` paste path awaits one real-session smoke
  test (primary monitor only for now). See
  [`docs/product/Platforms-and-Status.md`](docs/product/Platforms-and-Status.md).

## The UI

Two composers over the same config:

- **CLI** (`new` / `edit`) — headless and scriptable.
- **Visual composer** (`terminal-launcher gui`) — a native window (pywebview, no web
  server): a launchpad of workspace cards, a click-a-cell slot editor, and inline pane
  management. It opens **maximized**, and on a fleeting launch it closes behind you.

## Documentation

Full docs live in [`docs/`](docs/README.md):

- **[Product docs](docs/product/README.md)** — the product, for any stakeholder.
- **[Technical docs](docs/technical/README.md)** — the code, for developers.
- **[concept.md](docs/concept.md)** · **[decisions/](docs/decisions/)** — the canonical concept and the architecture decision records.

## Repository layout

```
bin/terminal-launcher        # executable entry point (symlink onto PATH)
terminal_launcher/
  cli.py                     # argparse + interactive composer
  config.py                  # config load/save/defaults, color map
  model.py                   # resolve a workspace → concrete slots (platform-agnostic)
  layouts.py                 # split-plans + capacity (terminal-agnostic; shared)
  backend.py                 # picks the terminal backend per platform
  iterm2_backend.py          # macOS terminal layer: iTerm2 Python API
  windows_terminal_backend.py # Windows terminal layer: `wt` + Win32 (ctypes)
  gui.py                     # visual composer (pywebview)
tests/                       # pytest unit tests (layouts, model, config)
workspaces.example.json      # seed config
packaging/                   # py2app macOS .app + PyInstaller Windows .exe
docs/                        # concept + decision records
```

## License

[MIT](LICENSE) © Dimitri Berardi
