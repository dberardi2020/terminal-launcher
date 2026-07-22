# Concepts

The whole product is five words. Learn these and you understand Terminal Launcher.

## Pane

A **pane** is a single terminal with a persistent **identity** — not a window
position, but a *who / where*: a named context you return to. An identity is four
fields:

| Field | Meaning |
|---|---|
| **Name** | What this pane is — e.g. `Docs`, `Backend`, `Notes`. |
| **Color** | A visual tag so the pane is recognizable at a glance, both in the config and (optionally) inside the launched Claude session via `/color`. |
| **Target** | The working directory it opens against (e.g. `~/code/project`). |
| **Model** | Which Claude model that pane runs — overridable per slot at compose time. |

Panes are **reusable**: define `Docs` once and drop it into as many workspaces as you
like. Colors come from a small named set (blue, orange, red, purple, green, cyan,
pink, gray).

## Layout

A **layout** is the shape of the arrangement — how many panes and how they're divided
on screen:

| Layout | Shape |
|---|---|
| **Single** | One pane, full window. |
| **Split** | Two panes, side by side. |
| **Combo** | Three panes — one full-height pane, two stacked beside it. |
| **Quad** | Four panes in a balanced 2×2 grid. |

**Split** and **Combo** can be **flipped** horizontally — which side the main pane
takes — and the flip is saved per workspace. (Single has nothing to mirror; Quad is
already symmetric.)

## Workspace

A **workspace** is a named, saved **composition**: a layout plus a specific pane
assigned to each slot. Workspaces are the everyday entry point — you pick one and
launch.

A slot may be left **intentionally empty**. On launch an empty slot is *dropped*, not
run as a blank shell — so a three-of-four-filled quad launches as three real panes,
never one dead rectangle. (Exactly *how* the gap is handled differs by backend; see
[Platforms & Status](platforms-and-status.md).)

## Composer

The **composer** is the interactive builder: choose a layout, then assign a pane and a
model to each slot. It comes in two forms over the **same** config:

- **CLI** (`new` / `edit`) — headless and scriptable, prompt-driven in the terminal.
- **Visual composer** (`terminal-launcher gui`) — a native window. A launchpad of
  workspace cards sits on top; below is a live composer where you pick a layout and
  **click a slot to fill it**. The slot editor is an inline side panel (headed
  *“Editing &lt;position&gt;”*) with a **click-to-fill** pane list and **model chips**
  (including a **Default** that uses the pane's own model). Panes are created and edited
  inline in that same panel — no separate screen.

## Actions

What you can *do*, in either composer:

| Action | Meaning |
|---|---|
| **Launch** | Open every pane in the composition at once, tiled in its layout. |
| **New** | Compose and save a fresh workspace. |
| **Edit** | Load a saved workspace, change it, and persist. |
| **Delete** | Remove a workspace. |
| **Pane-new** | Add a new reusable pane (a terminal identity) to the registry. |

## What actually runs in a pane

A **filled** slot runs `claude -n <name> --model <model>` with the pane's target as
its working directory. An **empty** slot launches nothing. After a pane starts, its
identity is applied: the pane's title is set to the pane name, and — optionally —
`/color <name>` is injected into the Claude session so the prompt bar carries the
pane's color.

## The genericness principle

Panes and workspaces are **data** — your configuration. The composer and launcher are
the **product**. Ship any pane set you like; nothing about the tool assumes a
particular one.

---

*This is the single source for the concept model. The decisions behind it live in
[`decisions/`](../decisions/); how it's realized in code is
[`technical/architecture.md`](../technical/architecture.md).*
