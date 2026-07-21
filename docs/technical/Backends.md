# Backends

The terminal-backend layer is where an abstract layout becomes real windows. It's the
part of the system with the most platform reality in it — and the part most carefully
sealed off behind a small contract so nothing above it has to care which terminal is
running.

## The contract

Both backend modules expose the **same three functions** (identical signatures):

```python
available() -> bool
describe(layout, slots, flip: bool = False) -> list[str]        # dry-run text
launch(layout, slots, inject_color: bool = False,
       workspace_name: str = "workspace", color_delay: float = 1.5,
       flip: bool = False) -> None
```

`slots` is a list of `model.ResolvedSlot`. `backend.py` is a pure router that forwards to
a selected implementation and adds `name()` / `install_hint()`.

## Selection (`backend.py`)

```python
def _impl():
    if iterm2_backend.available():            # macOS + iTerm2 installed
        return iterm2_backend
    if windows_terminal_backend.available():  # Windows + wt on PATH
        return windows_terminal_backend
    return None                               # no native backend here
```

- **macOS + iTerm2 → `iterm2_backend`.** `available()` requires `Darwin`,
  `/Applications/iTerm.app`, and an importable `iterm2` lib.
- **Windows + `wt` → `windows_terminal_backend`.** `available()` requires `Windows` and
  `shutil.which("wt")`.
- **Otherwise → none.** `available()` is False and `launch()` raises an actionable error.

`_impl()` runs fresh on every call — no caching — so installing a backend mid-session is
picked up next call. Importing this module is safe on every platform: each backend defers
its heavy OS dependency (the `iterm2` lib; `ctypes.windll` / `WINFUNCTYPE`) to
platform-only code paths, never at import.

## The shared model: one window per pane

Both backends realize the **same** model ([ADR 0008](../decisions/0008-one-window-per-pane-and-windows-terminal-backend.md)):
each *filled* slot is its own OS window placed at its slot rectangle; empty slots are left
as bare desktop (real gaps). There is no full-vs-partial divergence and no compaction — a
full quad is four windows in the four quadrants, just as a partial quad is however-many
windows with gaps where the empties are.

Placement is **self-owned geometry**, not the OS snap UI. Neither Windows nor macOS
exposes a supported way to *invoke* native snapping programmatically (only synthetic input
or the Accessibility/AX API), so each backend computes rectangles from the OS work area
and places its own windows there — deterministic, permission-light, and pixel-aligned to
where the OS would snap.

## `iterm2_backend.py` — the iTerm2 Python API

### Async on its own event loop
The build tree is `async def` (awaiting the iterm2 lib throughout). `launch()` creates a
**fresh `asyncio` event loop** and runs `iterm2.run_until_complete(main, retry=False)` —
its own loop because the launcher runs on a pywebview GUI worker thread with no ambient
loop.

### Auth: Automation, and why `retry=False`
iTerm2's Python API gets its auth cookie through iTerm2's AppleScript automation surface —
so this needs **Automation** permission (not Accessibility). The lib's built-in
connect-retry **loops forever** on an auth denial, so it's disabled; the code does its own
waiting in `_ensure_running()` and, on failure, re-raises a `RuntimeError` pointing at
*System Settings › Privacy & Security › Automation*.

### Bringing iTerm2 up without a rogue window
- `_ensure_running()` — if iTerm2 isn't running, `open -g -a iTerm` (background), poll
  `pgrep -x iTerm2` up to ~8 s, then a 1.5 s settle for the API socket.
- It **deliberately never re-`open`s an already-running iTerm2** — activating a zero-window
  iTerm2 pops an empty default window.
- `cold = not _is_running()` is captured *before* ensuring — it gates stray-window cleanup.

### Spawning & placing
- A **dynamic profile** is written first to
  `~/Library/Application Support/iTerm2/DynamicProfiles/terminal-launcher.json` (iTerm2
  hot-reloads that dir) — a dedicated One-Dark-ish / Menlo 13 profile that never touches the
  user's own profiles.
- Per-slot command + cwd ride in a write-only profile override (`LocalWriteOnlyProfile`):
  custom command `claude -n <name> --model <model>` (or the default shell for an empty
  slot), and a custom initial directory.
- `_build` creates one window per filled slot and `async_set_frame`s it to
  `_slot_rects(layout, flip)[slot.index]` (Cocoa coords, origin bottom-left; flip mirrors
  x). Screen size comes from **CoreGraphics via `ctypes`** (`CGMainDisplayID` /
  `CGDisplayBounds`) — permission-free, no AppleScript prompt — minus a 25 px menu bar.

### Stray-window cleanup
Only when `cold`, `_close_stray_default_window` closes a window **only** if it has exactly
one tab / one session whose name is a bare login shell (`_SHELL_NAMES = {-zsh, zsh, -bash,
…}`) — narrowly gated so it never kills a user's real window.

## `windows_terminal_backend.py` — `wt` + Win32 (ctypes)

- **Spawn.** One window per filled slot: `wt -w new -d <dir> --title <name> --tabColor <hex>
  claude -n <name> --model <model>`. `-w new` forces a separate window (not a tab);
  everything after the executable is passed to `claude` verbatim.
- **Discover.** `wt` returns immediately after handing off to a WindowsTerminal host process
  (new or existing), so the new window is found by **diffing the set of visible
  `CASCADIA_HOSTING_WINDOW_CLASS` windows** before/after the spawn — not by PID.
- **Place.** `SetWindowPos` to `_slot_rects(layout, flip)[slot.index]` (Win32 coords, origin
  top-left, from `SPI_GETWORKAREA`). Two passes: place, then read
  `DWMWA_EXTENDED_FRAME_BOUNDS` and re-place so the **visible** frame lands on the rect
  (Win11's invisible resize border would otherwise leave a seam gap). The process is made
  **per-monitor-DPI-aware** so coordinates are physical pixels. Primary monitor only for now.
- **64-bit HWND safety.** ctypes arg/restypes are configured (`_configure()`) so handles
  aren't truncated to 32-bit ints — the classic "wrong window" bug.
- **No permission prompt** — positioning a window you spawned needs none.

## Identity injection

Identity is three things — the window **name/title**, and the Claude-side **`/color`**
prompt tint:

| | iTerm2 | Windows Terminal |
|---|---|---|
| Name/title | `session.async_set_name(name)` | `wt --title <name>` (+ `--tabColor <hex>`) |
| `/color` delivery | `async_send_text` — **no focus needed** | **focus the window** (`AttachThreadInput`) then **type** via `SendInput` |
| Submit | separate `async_send_text("\r")` | separate Enter keystroke |

**The load-bearing gotcha (both backends):** a `/color <name>` command must be typed/sent and
then submitted, and Claude's slash-command autocomplete can eat characters. iTerm2 sends the
text then a lone CR. Windows has no per-pane send API, so it focuses the window and types the
command one character at a time with a small delay, dismissing any open autocomplete with
Escape first — so the space after `/color` isn't swallowed. See
[ADR 0002](../decisions/0002-identity-injection.md).

**Readiness.** Both wait before injecting: after the configured `color_delay`, iTerm2
`_wait_ready` polls the pane's screen text for markers (`"shift+tab"`, `"auto-accept"`, …);
the Windows backend polls the window title until it carries the pane name (Claude sets it via
`-n`) so the command lands in a ready prompt, not a booting TUI.

## Gotchas worth remembering

- The model is uniform — real desktop gaps on both platforms, no compaction anywhere.
- `wt` has **no per-pane text API** (unlike iTerm2's `send-text`); `/color` therefore needs
  real window focus on Windows, which is the one thing the injection path must get right.
- Set ctypes arg/restypes for any Win32 call taking an `HWND`, or 64-bit handles truncate.
- Placement compensates for the DWM invisible border; skipping that leaves visible seams
  between adjacent panes.
