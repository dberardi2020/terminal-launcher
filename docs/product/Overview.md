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

## Why it exists — rebuilt, not ported

Terminal Launcher is a **from-the-concept rebuild** of an earlier Windows/PowerShell
launcher. The predecessor was a WPF GUI (loading XAML) wired to one hard-coded set of
panes, launched through a `.vbs` script and Windows-specific window management.

That machinery was **incidental**. What was durable was the *idea*: reusable pane
identities, a small layout vocabulary, saved compositions, one-command launch. The
rebuild keeps only that idea and implements it fresh as a **thin Python core** driving
a **terminal backend** — iTerm2 on macOS, WezTerm elsewhere.

| | |
|---|---|
| ✓ **Essence — preserved** | Panes as reusable identities (`name · color · target · model`); the single/split/combo/quad layout vocabulary; workspaces as saved compositions; the composer + one-command launch. |
| ✗ **Incidental — dropped** | Windows & PowerShell; the `.vbs` launcher and shortcut installers; Windows-specific window placement; the fixed, hard-coded pane set. |

**The key principle:** the pane set is **data, not structure**. The old build shipped
one set of panes; Terminal Launcher is pane-agnostic — any names, targets, and colors
work. Panes and workspaces are *your configuration*; the composer and launcher are the
product.

## Who it's for

- Anyone who runs **several Claude Code sessions in parallel** and wants them tiled,
  named, and reproducible.
- People who want a **saved, one-command** way back into a familiar multi-terminal
  setup instead of rebuilding it each session.
- macOS users today (verified end-to-end on iTerm2); cross-platform by construction,
  with a WezTerm backend for elsewhere — see [Platforms & Status](Platforms-and-Status.md).

## Next

- The vocabulary behind all of this → [Concepts](Concepts.md).
- Getting it running and composing your first workspace → [User Guide](User-Guide.md).
