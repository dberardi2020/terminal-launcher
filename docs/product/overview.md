# Overview

## The problem

When you work with Claude Code, you often want **more than one session open at
once** — each pointed at a different part of your work: docs in one, the backend in
another, notes in a third. You want them **laid out side by side** so you can see
them together, and you want the same arrangement back **tomorrow** without
rebuilding it by hand every morning.

Opening those terminals one at a time, sizing them, `cd`-ing each to the right
place, and starting Claude with the right model in each — that's a chore you repeat
constantly. Terminal Launcher removes it.

## The solution

Define your terminals **once** as reusable **panes**, arrange them into a
**layout**, save that arrangement as a **workspace**, and launch the whole tiled set
with **one command**:

```sh
terminal-launcher launch Docs
```

That opens every pane in the workspace at once — tiled in its layout, each in its
target directory, each running Claude Code with its assigned model, each named and
color-tagged so you know at a glance which is which.

There are two ways to build a workspace: a scriptable **CLI** (`new` / `edit`) and a
native **visual composer** (`terminal-launcher gui`) — a drag-free, click-to-fill
window for arranging slots and managing panes. Both read and write the same config.

## How it's built

Terminal Launcher is a **thin Python core** — config plus a composition model — driving a
**terminal backend** behind one small interface: iTerm2 on macOS, Windows Terminal on
Windows. The core is platform-agnostic; each backend is a thin driver that spawns and
places native windows. Adding a platform is one new module, not a fork.

**The load-bearing principle:** the pane set is **data, not structure**. Nothing about any
particular set of panes is baked in — any names, targets, and colors work. Panes and
workspaces are *your configuration*; the composer and launcher are the product. That is
what lets one install serve any workflow.

## Who it's for

- Anyone who runs **several Claude Code sessions in parallel** and wants them tiled,
  named, and reproducible.
- People who want a **saved, one-command** way back into a familiar multi-terminal
  setup instead of rebuilding it each session.
- macOS (verified end-to-end on iTerm2) and Windows (native Windows Terminal backend) —
  see [Platforms & Status](platforms-and-status.md).

## Next

- The vocabulary behind all of this → [Concepts](concepts.md).
- Getting it running and composing your first workspace → [User Guide](user-guide.md).
