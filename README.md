# Terminal Launcher

Compose and launch tiled Claude Code sessions with one command.

You often want several Claude Code sessions open at once — each pointed at a
different part of your work, laid out side by side so you can see them together.
Terminal Launcher lets you define those terminals once as reusable **panes**,
arrange them into a **layout**, save the arrangement as a **workspace**, and
launch the whole set — tiled, named, and color-tagged — in a single WezTerm
window.

It is a macOS-native (and cross-platform) **rebuild from the concept, not a port**,
of an earlier Windows/PowerShell launcher: the durable idea is preserved; the
Windows/WPF machinery is gone. See [`docs/concept.md`](docs/concept.md) for the model
and [`docs/decisions/`](docs/decisions/) for why it's built the way it is.

## Model, in three words

- **Pane** — a terminal identity: `name · color · target dir · model`. Reusable.
- **Layout** — the shape: `single` (1), `split` (2 side-by-side), `combo` (3 — one
  full pane + two stacked), `quad` (2×2). `split` and `combo` can be **flipped**
  horizontally (saved per workspace). Leave slots empty and a partial layout
  **compacts** to the filled count on launch — no empty shells. See
  [`docs/decisions/0005`](docs/decisions/0005-combo-flip-and-partial-compaction.md).
- **Workspace** — a saved composition: a layout with a pane assigned to each slot.

Panes and workspaces are *data* (your config); the composer and launcher are the
product. Ship any pane set you like.

## Requirements

- **Python 3.10+** (uses `from __future__ import annotations`; developed on 3.14).
- **[WezTerm](https://wezterm.org)** on your `PATH` — the terminal layer.
  `brew install --cask wezterm` (macOS) · `winget install wez.wezterm` (Windows).
- **Claude Code** (`claude`) on your `PATH` — what each filled pane runs.

## Install

No build step. Symlink the entry point onto your `PATH`:

```sh
ln -s "$(pwd)/bin/terminal-launcher" ~/.local/bin/terminal-launcher
```

Then create a starter config and compose your first workspace:

```sh
terminal-launcher init        # seed ~/.config/terminal-launcher/workspaces.json
terminal-launcher new         # interactively compose + save a workspace
terminal-launcher launch Docs # tile it up
```

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

The interactive `new` / `edit` / `pane-new` verbs **write back to the config** —
fixing the old GUI's file-only-editing limitation.

## Configuration

One JSON file is the single source of truth for panes, workspaces, and settings.
Resolution order:

1. `--config <path>` or `TERMINAL_LAUNCHER_CONFIG`
2. `$XDG_CONFIG_HOME/terminal-launcher/workspaces.json`
3. `~/.config/terminal-launcher/workspaces.json`

See [`workspaces.example.json`](workspaces.example.json) for the shape. Model
precedence when launching a slot: **slot override → pane default → global default**.

## Identity in-session

A launched pane carries its identity three ways: the WezTerm **session name**
(`claude -n <name>`), the **tab title** (`set-tab-title`), and — optionally — the
Claude prompt-bar **color** (`/color <name>`, injected with `--inject-color` or
`settings.injectColor`). Injection targets a specific pane by id, so it needs no
Accessibility permissions. See
[`docs/decisions/0002-identity-injection.md`](docs/decisions/0002-identity-injection.md).

## Platform status

- **macOS** — working and verified end-to-end (spawn, tile, name, title, color).
- **Windows** — **unverified**. The launcher drives `wezterm cli`, which is
  identical on both platforms, so the commands are the same; only the initial GUI
  start differs (`wezterm-gui start`). Verify before relying on it.

## The UI

Two composers over the same config:

- **CLI** (`new` / `edit`) — headless and scriptable.
- **Visual composer** (`terminal-launcher gui`) — a native window (pywebview, no web
  server): a launchpad of workspace cards, a click-a-cell slot editor, and inline pane
  management. It opens **maximized**, and on a fleeting launch it closes behind you.
  See [`docs/decisions/0003-visual-composer-pywebview.md`](docs/decisions/0003-visual-composer-pywebview.md).

## Layout

```
bin/terminal-launcher        # executable entry point (symlink onto PATH)
terminal_launcher/
  cli.py                     # argparse + interactive composer
  config.py                  # config load/save/defaults, color map
  model.py                   # resolve a workspace → concrete slots (platform-agnostic)
  wezterm.py                 # the terminal layer: drives `wezterm cli`
workspaces.example.json      # seed config
docs/                        # concept + decision records
```
