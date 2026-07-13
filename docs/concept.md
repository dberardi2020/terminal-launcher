# Terminal Launcher — Concept

*A composer and launcher for arranging several Claude Code sessions on screen at once.*

The **as-built** concept: it describes what Terminal Launcher *is*, not a draft of
what it might become.

## The idea, in one paragraph

You often want more than one terminal open at the same time — each running Claude
against a different part of your work — laid out side by side so you can see them
together. Terminal Launcher lets you define those terminals once as reusable
**panes**, arrange them into a **layout**, save the arrangement as a
**workspace**, and launch the whole set with one command.

**Rebuilt, not ported.** The predecessor was a Windows/PowerShell GUI (WPF loading
XAML) built for one hard-coded set of panes. That machinery — PowerShell, the `.vbs`
launcher, Windows window management, the fixed pane set — was incidental. Terminal
Launcher keeps only the durable idea and implements it fresh: a **thin Python core**
driving **WezTerm** as the terminal layer (see
[`decisions/0001-terminal-layer-and-core.md`](decisions/0001-terminal-layer-and-core.md)).

## Core concepts

### Pane

A single terminal with a persistent **identity** — launched at its target
location, running Claude with an assigned model. A pane is not a window position;
it's a *who/where*: a named context you return to. Identity is four fields:

- **Name** — what this pane is (e.g. `Docs`, `Backend`).
- **Color** — a visual tag so a pane is recognizable at a glance, both in the
  config and (via `/color`) in the launched session itself.
- **Target** — the working directory it opens against.
- **Model** — which Claude model that pane runs (overridable per slot at compose time).

### Layout

The shape of the arrangement — how many panes and how they're divided on screen:

- **Single** — one pane, full window.
- **Split** — two panes, side by side.
- **Quad** — four panes in a balanced 2×2 grid.

### Workspace

A named, saved **composition**: a layout plus a specific pane assigned to each
slot (a slot may be intentionally empty — it launches a plain shell). Workspaces
are the everyday entry point — you pick one and launch. (The config key is
`workspaces`.)

### Composer

The interactive builder. Choose a layout, then assign a pane and model to each
slot. Two forms exist:

- **CLI** (`new` / `edit`) — headless and scriptable.
- **Visual composer** (`terminal-launcher gui`) — a native window. Its **slot editor**
  is an **inline side panel**, not a modal: selecting a slot opens an editor headed
  *“Editing &lt;position&gt;”* (slots are named by position — *Left/Right*, or the quad
  corners), with a **click-to-fill** pane list (clicking a pane assigns it immediately)
  and **model chips** including a **Default** (use the pane's own default). Editor verbs
  are *Clear slot* / *Done*; composition verbs (*Launch · Save as new · Update · Revert
  · Clear*) sit in the footer. Panes are created and edited inline in the same side
  panel — no separate screen.

See [`decisions/0003-visual-composer-pywebview.md`](decisions/0003-visual-composer-pywebview.md).

## Actions

| Action | Meaning |
|---|---|
| **Launch** | Open every pane in the composition at once, tiled in its layout. |
| **New** | Compose and save a fresh workspace. |
| **Edit** | Load a saved workspace, change it, and persist. |
| **Delete** | Remove a workspace. |
| **Pane-new** | Add a new reusable pane (terminal identity) to the registry. |

## Interaction flow

- **Fast path** — `terminal-launcher launch Docs` → the arrangement opens.
- **Compose path** — `terminal-launcher new` → pick a layout → assign each slot →
  it saves, then previews.
- **Tweak path** — `terminal-launcher edit Docs` → reassign a slot / change layout
  → it persists.

## What runs in a pane

A filled slot runs `claude -n <name> --model <model>` with the pane's target as
the working directory. An empty slot is left as a plain shell. Identity is then
applied: the WezTerm tab title is set to the pane name, and (optionally) `/color
<name>` is injected into the Claude session. See
[`decisions/0002-identity-injection.md`](decisions/0002-identity-injection.md).

## Essence vs. incidental

- ✓ **Essence — preserved.** Panes as reusable identities (`name · color · target
  · model`). The layout vocabulary (single/split/quad). Workspaces as saved
  compositions. The composer + launch. One-command launch of a whole multi-pane
  arrangement.
- ✗ **Incidental — dropped.** Windows & PowerShell. The `.vbs` launcher and
  shortcut installers. Windows-specific window placement. The specific hard-coded
  pane set.

**The key genericness principle:** the pane set is **data, not structure**. The
prior build shipped one set of panes; the concept is pane-agnostic — any
names/targets/colors work. Panes and workspaces are user configuration; the
composer and launcher are the product.

## Deferred

- **Dock app packaging** — the visual composer runs via `terminal-launcher gui`;
  bundling it into a double-clickable `.app` is pending. ADR 0003.
- **Windows verification** — the WezTerm layer is cross-platform by construction
  but has only been run on macOS.
- **Heterogeneous panes** — non-terminal panes (a browser, a file manager) tiled
  alongside Claude terminals; needs an OS-window placement layer. ADR 0004.
- **Directory-owned identity** — whether a pane's identity should travel with its
  repo rather than live only in this config. Open.
