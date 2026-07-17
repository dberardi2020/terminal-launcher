# 0007 — macOS terminal layer: iTerm2 backend & real-gap partial layouts

**Status:** Accepted · **Date:** 2026-07-16

## Context

[ADR 0001](0001-terminal-layer-and-core.md) chose **WezTerm** as the single
terminal layer, driven by a thin Python core, with cross-platform parity as the
decisive advantage. In practice, WezTerm on **macOS** could not deliver the one
thing the launcher exists to provide — *deterministic* placement of named panes:

- `--class` (the handle for addressing a specific GUI window) is X11/Wayland-only;
  on macOS it is a no-op, so windows couldn't be reliably targeted.
- WezTerm's macOS multiplexer / workspace / instance model made "control *this*
  window" ambiguous, and panes intermittently rendered invisible.

Cross-platform parity — 0001's core reason — is real, but it bought nothing on the
one platform actually in use. The reliability the launcher needs was missing
exactly where it runs.

## Decision

**Split the terminal layer by platform, behind a backend seam.**

- **macOS → iTerm2** (`iterm2_backend.py`), via iTerm2's Python API. We hold direct
  `Session` references to exactly the panes we create — unambiguous per-pane
  control, native windows, no Accessibility.
- **Everything else → WezTerm** (`wezterm.py`) — unchanged; still the (unverified)
  Windows path.
- **`backend.py`** selects: iTerm2 on Darwin when installed, WezTerm otherwise
  (including a macOS fallback if iTerm2 is absent).

The app talks to **one interface** — `available()` / `describe()` / `launch()` — so
the backends are interchangeable. The split-plans moved to `layouts.py`
(terminal-agnostic, unit-tested) and are shared by both backends.

## Consequences

### iTerm2 auth needs Automation permission (not Accessibility)

iTerm2's Python API obtains its auth cookie via an AppleScript Apple Event to
iTerm2, so:

- the py2app bundle declares `NSAppleEventsUsageDescription` — macOS then shows the
  consent prompt instead of silently denying the Apple Event;
- the API is connected with `retry=False` — its built-in retry loops *forever* on an
  auth failure, so we never use it (`_ensure_running()` waits for iTerm2 instead);
- first launch prompts *"Terminal Launcher wants to control iTerm2"*; a denial
  yields a clear, actionable error pointing at System Settings › Privacy &
  Security › Automation.

This is a lighter, one-time consent than the **Accessibility** grant 0001 feared —
and it is what makes per-pane targeting (and `/color` injection) reliable on macOS.

### Real-gap partial layouts — this reverses ADR 0005's Decision 3 on macOS

[ADR 0005](0005-combo-flip-and-partial-compaction.md) chose **compaction** for
partial layouts (drop empties, reshape the filled panes to fit) and explicitly
**rejected** the OS-window "preserve the gap" option because, under WezTerm,
drawing a gap needed Accessibility. iTerm2 removes that premise: it gives real,
permission-free window placement. So the iTerm2 backend **keeps the gap** — each
filled slot opens as its own window at its true screen rectangle (`_slot_rects`
per layout), and empty slots are left as bare desktop.

The two backends now differ deliberately:

| | Full layout | Partial layout |
|---|---|---|
| **iTerm2 (macOS)** | one maximized split-pane window | one window per filled slot at its slot rect; empties left as **desktop gaps** |
| **WezTerm (other)** | one split-pane window | **compacts** (0005) — no gap primitive without Accessibility |

0005's compaction reasoning still holds *for WezTerm*; it is superseded only on the
iTerm2 path.

### Other

- **Styled dynamic profile.** iTerm2 launches use a dedicated hot-reloaded profile
  (`terminal-launcher.json`, One Dark-ish, Menlo 13) so appearance is consistent
  and never touches the user's own profiles. Theming stays configurable, deferred.
- **Self-validation became possible.** iTerm2 exposes window/session state over the
  same API, so a launch can be verified by read-back (plus `screencapture`) without
  a human — the WezTerm era had no equivalent.
- **`wezterm.py` still carries its own `SPLIT_PLAN`** — reconciling it with
  `layouts.py` (single source of truth) is open backlog.
- **TCC persistence.** An unsigned py2app bundle may re-prompt for Automation after
  each rebuild (acceptable for a personal tool; ad-hoc signing would stabilize it).
- **ADR 0001 is amended, not superseded** — WezTerm remains the non-macOS backend,
  and the thin-core / backend-seam design 0001 established is what made this swap a
  single new module.
