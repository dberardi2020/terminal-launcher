# 0008 — One window per pane (all layouts) + a Windows Terminal backend; WezTerm removed

**Status:** Accepted · **Date:** 2026-07-21

## Context

After [ADR 0007](0007-iterm2-backend-and-real-gap-layouts.md) the terminal layer had two backends behind the seam:

- **iTerm2 (macOS)** — a *full* layout opened as one maximized split-pane window; a *partial* layout opened one window per filled slot at its real rectangle (real desktop gaps).
- **WezTerm (everywhere else)** — one split-pane window, *compacting* partial layouts (drop empties) because it cannot leave a hole. This was also the "someday Windows" path, and it was never verified there.

Two things were unsatisfying:

1. **Two divergent layout models.** Real gaps vs compaction; separate windows vs one split window. The same workspace was structurally different depending on backend, and the divergence kept `compact()`, a duplicated split-plan inside `wezterm.py`, and a fork in the docs alive.
2. **No native Windows story.** The goal is for Windows to feel like macOS does now — real, separately-placed OS windows — not WezTerm's single-window multiplexer. WezTerm-on-macOS is exactly what motivated the iTerm2 move (0007); WezTerm-on-Windows would carry the same single-window feel.

We also weighed *leveraging the OS's native snapping* (macOS tiling, Windows Snap) for alignment. Neither OS exposes a supported way to **invoke** snapping programmatically — the only routes are synthesizing user input (fragile, timing-dependent) or the Accessibility/AX API (the very permission 0005/0007 were maneuvering to avoid). Self-placing a window at the snap *rectangle* gives identical alignment deterministically — which is what iTerm2 already does with `async_set_frame`.

## Decision

**One uniform model on every platform, and a native backend per platform.**

1. **One real OS window per pane, in every layout, placed by geometry.** Each filled slot opens as its own window at its slot rectangle (derived from the OS work area); empty slots are left as bare desktop (real gaps); no internal terminal splits. This *extends 0007's real-gap approach from partial layouts to all layouts* — a full quad is four windows in four quadrants, not one split-pane window.

2. **Add a native Windows Terminal backend** (`windows_terminal_backend.py`) that realizes the same model on Windows: spawn one `wt` window per slot, discover its window, and place it with `SetWindowPos` (compensating for per-monitor DPI and the DWM invisible border). Pure `ctypes`, no new dependency, no permission prompt.

3. **Remove the WezTerm backend and `compact()`.** With two native geometry backends, WezTerm's cross-platform parity bought nothing on the platforms in use, and it was the only thing keeping the divergent single-window / compaction model alive. It is re-addable later as a deliberate module (e.g. a Linux backend, where `--class` works) if an unknown-platform seat is ever wanted.

`backend.py` now routes `Darwin → iTerm2`, `Windows → Windows Terminal`, and reports no backend elsewhere. The `available()` / `describe()` / `launch()` contract is unchanged.

## Consequences

### Supersessions

- **Supersedes ADR 0005's Decision 3 (partial compaction) on all platforms.** 0007 had already reversed it on the iTerm2 path; with WezTerm gone, compaction is removed entirely.
- **Supersedes 0007's full-layout behavior on macOS.** iTerm2's split-pane build for full layouts is retired; every layout now uses the separate-window path (`_slot_rects`).
- **Further amends ADR 0001.** WezTerm — 0001's terminal layer, already displaced on macOS by 0007 — is now removed everywhere. The thin-core / backend-seam design 0001 established is unchanged, and is exactly what made both this and the 0007 swap single-module changes.

### Placement is self-owned geometry, not OS snapping

Both backends place their *own* windows at computed rectangles — iTerm2 via `async_set_frame`, Windows Terminal via `SetWindowPos` — sourced from the OS work area so the alignment matches where the OS would snap. This is deterministic and permission-light. The only thing forgone is the OS *snap-group* behavior (taskbar grouping, shared-edge linked-resize), which is not programmatically creatable anyway and is undesirable for independent sessions.

### Windows specifics

- **No permission prompt** — unlike macOS's Automation consent for the iTerm2 API, positioning a window you spawned needs none.
- **No per-pane text API.** `wt` has no equivalent of iTerm2's `send-text`, so `/color` is injected by focusing the target window (`AttachThreadInput` to steal focus reliably) and typing via `SendInput` Unicode — Escape first, then per-character with a small delay, so Claude's slash-command autocomplete can't intercept and corrupt the command.
- **DWM + DPI compensation.** Win11 windows carry an invisible resize border; the placer reads `DWMWA_EXTENDED_FRAME_BOUNDS` and re-places so the *visible* frame lands exactly on the slot rect. The process is made per-monitor-DPI-aware so coordinates are physical pixels. **Primary monitor only** for now.
- **64-bit HWND safety.** ctypes arg/restypes are set so window handles aren't truncated to 32 bits.

### Other

- **Import safety.** `backend.py` imports both native backends on every platform; each defers its heavy OS dependency (the `iterm2` lib; `ctypes.windll` / `WINFUNCTYPE`) to platform-only code paths, never at import time.
- **`layouts.py` split-plans** (`plan()` / `SPLIT_PLAN`) are now used only to derive `CAPACITY` and by the unit tests — the native backends need slot *rectangles*, not split directions. The duplicated split-plan in `wezterm.py` is gone with the file.
- **Packaging.** macOS keeps py2app; Windows gets a PyInstaller spec (plus a zero-bundle `pythonw -m terminal_launcher gui` shim). See [Build, Packaging & Testing](../technical/Build-Packaging-Testing.md).
- **What's verified.** On Windows: geometry, window discovery, placement, and DWM compensation are live-tested (the visible frame lands pixel-exact). The `claude` spawn + `/color` keystroke path is written to the proven pattern but awaits a real-session smoke test.
