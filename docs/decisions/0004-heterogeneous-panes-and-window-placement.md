# 0004 — Heterogeneous panes & window placement

**Status:** Proposed (future direction — not yet built) · **Date:** 2026-07-13

## Context

Today every pane is a Claude terminal, tiled *inside one WezTerm window*. A
wanted future workflow is a **mixed** workspace — a Claude terminal alongside a
**Chrome** window, a **Finder** window, or any other app. WezTerm cannot do this:
a multiplexer pane can only run a *terminal program*, never a GUI app. So mixed
workspaces are outside WezTerm's model entirely, and this needs a different layout
mechanism. This ADR records the direction; it revisits the terminal-layer call in
[ADR 0001](0001-terminal-layer-and-core.md).

## The two layout models

There are two fundamentally different ways to tile a screen:

| Model | Tiles | Holds Chrome / Finder? |
|---|---|---|
| **In-terminal multiplexer** (WezTerm — today) | panes inside one terminal window | No — a pane runs a terminal program, not a GUI app |
| **OS-window tiler** | independent application windows on screen | Yes — any window can be placed |

WezTerm is the first. The predecessor was the second (Windows WPF
arranging OS windows across virtual desktops) — which would have supported a
Chrome pane natively. Choosing WezTerm (ADR 0001) traded OS-window generality for
terminal-tiling wins: clean identity, deterministic splits, and — importantly —
no Accessibility permission. Heterogeneous panes are the requirement that pulls
back toward the OS-window model for the mixed case.

## The unavoidable constraint

Positioning an *arbitrary* app's window on macOS (Chrome, Finder) goes through the
**Accessibility API** (`AXPosition` / `AXSize`). There is **no permission-free
path** — unlike WezTerm, which we drive through a CLI, arbitrary apps expose no
such control surface. So any mixed workspace implies an Accessibility grant. This
is the same cost the original Windows app effectively paid via window management.

## Decision (direction)

Two additive changes; neither breaks the all-terminal path.

### 1. Typed panes — a launcher registry

Generalize a pane from "always Claude" to a `kind` with a launcher per kind:

- `claude`  → open a WezTerm window running `claude -n <name> --model <model>`
- `app`     → `open -a "<Application>"` (e.g. Chrome)
- `path`    → `open <dir>` → a Finder window
- `url`     → open a browser at a URL
- `command` → any GUI/CLI program

The config gains a per-pane `"kind"` (default `claude`, so existing configs are
unchanged). `ResolvedSlot` grows a `kind` plus each kind's "how to launch / how to
find its window" behaviour.

### 2. A screen-region window-placement layer

The layout (single/split/quad) computes a **rectangle per slot** on the target
display. After launching each slot's window, a platform *placer* moves it into its
rectangle. WezTerm windows are placed exactly like Chrome windows — WezTerm stops
owning the layout and becomes just one window type. (This reintroduces the
screen-rect math `model.py` had before it was stripped for WezTerm.)

macOS placer options, trading dependency vs. who holds the permission:

| Placer | Extra install | Who needs Accessibility |
|---|---|---|
| **pyobjc + AXUIElement** | none (self-contained) | *our* process |
| **`yabai`** (shell out) | yabai | yabai (move/resize works without disabling SIP) |
| **Hammerspoon** (shell out) | Hammerspoon | Hammerspoon |

Delegating to `yabai`/Hammerspoon is attractive: it keeps the Accessibility grant
**off** our fleeting launcher (which exits right after handoff) and on a dedicated
window-manager tool.

## Recommended shape — hybrid, not all-or-nothing

- **All-terminal workspace** → keep today's WezTerm internal tiling. Common case,
  proven, needs no Accessibility. Do not regress it.
- **Mixed workspace** (any non-`claude` pane) → use the OS-window placer: every
  pane, including terminals (now standalone WezTerm windows), is launched and
  positioned into its rectangle.

The `kind` field decides which engine a workspace uses. The UI, config, identity
model, and fleeting-launch flow are unchanged; only a launcher-per-kind and a
placer module are added.

**Identity generalizes cleanly.** A pane stays a "who/where": a Chrome pane's
target is a URL/profile, a Finder pane's is a directory. Name + color still apply
(window title where the app allows; color is best-effort per app).

**Windows parity.** Same shape — the placer is per-platform (macOS = AX / yabai;
Windows = `SetWindowPos` via pywin32, or PowerToys FancyZones), but the typed-pane
model and rectangle math are shared. Consistent with ADR 0001's thin-client stance.

## Consequences

- Mixed workspaces require an Accessibility grant — ideally delegated to
  `yabai`/Hammerspoon rather than held by the launcher.
- Reintroduces an OS-window tiling layer (screen rectangles + a placer), partially
  revisiting ADR 0001 — but only for heterogeneous workspaces; the all-terminal
  path keeps WezTerm's advantages.
- Matching "the window we just launched" to its Accessibility reference (timing,
  apps that reuse existing windows) is the real implementation risk; prototype the
  placer against Chrome + Finder before committing.
- Not scheduled. Recorded so the path is known and ADR 0001 carries an honest
  annotation.
