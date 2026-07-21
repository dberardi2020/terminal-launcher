# 0003 — Visual composer: a fleeting native window (pywebview)

**Status:** Accepted · **Date:** 2026-07-13

## Context

The design splits into two independent decisions: the *terminal layer*
([ADR 0001](0001-terminal-layer-and-core.md)) and the *composer UI*. This ADR
records the composer.

Two things shaped it. First, the tool is **fleeting**: you open it, compose or pick
a workspace, launch, and it gets out of the way — the open → launch → gone feel of a
native desktop app. Second, two composers are wanted: a **headless CLI** for scripting,
and a **visual, dockable composer** for everyday use.

## Decision

**A CLI composer plus a visual composer that is a fleeting native window (pywebview),
both over the same `workspaces.json`.**

- **CLI** (`new` / `edit` / `pane-new`) — headless, scriptable; writes back to config.
- **Visual composer** (`terminal-launcher gui`) — pywebview renders local HTML/CSS/JS
  in the OS's **native WebView** (WKWebView on macOS, WebView2 on Windows) and bridges
  UI events straight into the same Python core (`config` + `wezterm`). **No web server,
  no persistent process** — the window *is* the app.
- **Fleeting launch** — once a launch is fully handed off, the process exits, so the
  composer disappears behind you; the WezTerm window and Claude sessions are
  independent processes and live on.

## Options weighed

| Option | Fleeting native window | Reuses HTML UI | New toolchain |
|---|---|---|---|
| **pywebview** (chosen) | yes — closes cleanly | yes, directly | none (stays in Python) |
| Server-backed web app | **no** — a persistent server is the opposite ethos | yes | a running server |
| Tauri | yes | yes | Rust + build step |
| SwiftUI / Avalonia | yes | no (rewrite UI) | Swift / .NET |
| CLI only | n/a | n/a | none, but no visual composer |

- **Server-backed web app — rejected outright.** A long-running localhost server
  directly contradicts the fleeting ethos.
- **Heavy native frameworks (SwiftUI / Avalonia / Tauri) — rejected as overkill.** A
  compiled native app is the eventual Dock form, but rewriting the UI in Swift or C# or
  adding a Rust build toolchain is too much for a personal fleeting tool. pywebview
  reuses the HTML/CSS/JS UI and the existing Python core with no new language.

## The interaction

The visual composer is a **launchpad of workspace cards** above a live **composer**.
The **slot editor is an inline side panel, not a modal**: selecting a slot opens an
editor headed *“Editing ‹position›”* (slots named by position — *Left/Right*, or the
quad corners), with a **click-to-fill** pane list (clicking a pane assigns it
immediately) and **model chips** including a **Default** (inherit the pane's own
default). Editor verbs are *Clear slot / Done*; composition verbs (*Launch · Save as
new · Update · Revert · Clear*) sit in the footer; per-workspace verbs (*Rename ·
Duplicate · Delete*) on each card's **⋯** menu. **Panes are created and edited inline**
in the same side panel (each pane row has an edit affordance; a **⚙ Panes** button
opens the full registry) — so the whole config is editable from the window, no modals.

## Consequences

- **Fleeting close is `os._exit(0)`** from the launch worker thread. pywebview's
  `window.destroy()` proved unreliable when called from a non-managed thread in this
  build, and the process *is* the app, so exiting is the clean, deterministic close.
- **The launch runs on a background thread** — doing it on the GUI thread beachballs
  the window (it sleeps for color-injection timing), and destroying from inside a
  JS-API call deadlocks.
- **Opens maximized** — pywebview `maximized=True`; the launched WezTerm window is
  maximized by the mechanism in ADR 0001 / [0002](0002-identity-injection.md).
- **One source of truth** — CLI and visual composer read/write the same
  `workspaces.json`, so they never diverge.
- **Pending:** packaging into a double-clickable Dock `.app` (via `py2app`). Until
  then the composer runs from `terminal-launcher gui`.
