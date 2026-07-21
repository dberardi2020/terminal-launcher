# User Guide

From nothing to a tiled, one-command Claude Code workspace.

## 1. Requirements

- **Python 3.10+** (developed on 3.14).
- **A terminal backend** — the layer that spawns and tiles the panes:
  - **macOS → [iTerm2](https://iterm2.com)** — `brew install --cask iterm2`.
  - **Windows → [Windows Terminal](https://aka.ms/terminal)** — `winget install Microsoft.WindowsTerminal`.
- **Claude Code** (`claude`) on your `PATH` — what each filled pane runs.

See [Platforms & Status](Platforms-and-Status.md) for details and permissions.

## 2. Install

Install the command with [pipx](https://pipx.pypa.io) — same on macOS, Linux, and Windows:

```sh
pipx install git+https://github.com/dberardi2020/terminal-launcher.git
```

That puts `terminal-launcher` on your `PATH` in an isolated environment. Prefer no install
at all? Clone the repo and run it as a module — `python3 -m terminal_launcher …`
(`py -m terminal_launcher …` on Windows).

On macOS you can also build a double-clickable **Dock app** for the visual composer
(py2app) — see [`packaging/README.md`](../../packaging/README.md).

## 3. Create your config

```sh
terminal-launcher init
```

This seeds a starter config at `~/.config/terminal-launcher/workspaces.json` from the
bundled example — a few sample panes and workspaces to edit. This one JSON file is the
single source of truth for your panes, workspaces, and settings.

## 4. Compose a workspace

You have two equivalent ways to build one. Both read and write the same config.

### The terminal (scriptable)

```sh
terminal-launcher new          # compose + save a new workspace
terminal-launcher edit Docs    # load an existing one, change it, persist
terminal-launcher pane-new     # add a new reusable pane
```

Each is prompt-driven: pick a layout, assign a pane (and optionally a model) to each
slot, and it **writes back to the config** when you're done.

### The visual composer

```sh
terminal-launcher gui
```

A native window opens (maximized). At the top is a **launchpad** of workspace cards —
each with a **Launch** button and a `⋯` menu (Rename · Duplicate · Delete · jump to
front/end). Below is the **composer**:

1. Pick a layout — **Single · Split · Combo · Quad**.
2. **Click a slot** to fill it. An inline side panel opens (*“Editing ‹position›”*)
   with a **click-to-fill** list of your panes — click one to assign it immediately —
   and **model chips**, including a **Default** chip that uses the pane's own model.
3. Manage panes inline in that same panel (the `⚙ Panes` button opens the full
   registry); create and edit panes without leaving the composer.
4. Use the footer verbs — **Launch · Save as new · Update · Revert · Clear** — to
   persist or run the composition.

When you launch from the composer, it hands off and **closes behind you**.

## 5. Launch

The fast path, once a workspace exists:

```sh
terminal-launcher launch Docs
```

Every pane opens at once, tiled in its layout, each in its target directory running
Claude with its assigned model. Useful flags:

- `--dry-run` — print the launch plan without opening anything.
- `--inject-color` — type `/color <name>` into each session so the Claude prompt bar
  carries the pane's color (see *Identity in-session* below).

## 6. Command reference

| Verb | What it does |
|---|---|
| `list` | List saved workspaces. |
| `panes` | List configured panes. |
| `preview <name>` | Text preview of a workspace's layout. |
| `launch <name>` | Launch a workspace. `--dry-run` prints the plan; `--inject-color` injects `/color`. |
| `new` | Interactively compose a **new** workspace and save it. |
| `edit <name>` | Interactively edit an existing workspace. |
| `delete <name>` | Remove a workspace. |
| `pane-new` | Interactively add a new pane (terminal identity). |
| `gui` | Open the visual composer. |
| `init` | Create a starter config from the bundled example. |
| `restore` | Re-apply this pane's `/color` + `/rename` after Claude Code's `/clear` (`--detect-only` to check without injecting). |

## 7. Identity in-session

A launched pane carries its identity three ways:

- **Session name** — `claude -n <name>`.
- **Pane title** — the iTerm2 session name (macOS) or the `wt` tab title (Windows).
- **Color** *(optional)* — `/color <name>` injected into the Claude prompt bar, via
  `--inject-color` or `settings.injectColor`. Injection targets a specific pane
  directly, so it needs no Accessibility permission.

**After `/clear`:** Claude Code's `/clear` (and reconnecting) resets the in-session colour
and name. Run **`/restore`** in the pane to re-apply them — it detects which pane you are by
directory and re-issues `/color` + `/rename`. Install the slash command with
`./integrations/claude-code/install.sh` (it runs `terminal-launcher restore`). See
[ADR 0009](../decisions/0009-restore-pane-identity.md).

## 8. Configuration essentials

The config resolves in this order:

1. `--config <path>` or the `TERMINAL_LAUNCHER_CONFIG` env var
2. `$XDG_CONFIG_HOME/terminal-launcher/workspaces.json`
3. `~/.config/terminal-launcher/workspaces.json`

**Model precedence** when launching a slot: **slot override → pane default → global
default** (`settings.defaultModel`). Colors come from a named set (blue, orange, red,
purple, green, cyan, pink, gray). For the full JSON shape, see
[`workspaces.example.json`](../../workspaces.example.json), and for the field-by-field
schema, the Technical [Data Model & Config](../technical/Data-Model-and-Config.md) doc.
