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

`slots` is a list of `model.ResolvedSlot`. `backend.py` is a pure router that re-exports
these plus `name()` and `install_hint()`, forwarding to a selected implementation.

## Selection & fallback (`backend.py`)

```python
def _impl():
    if platform.system() == "Darwin" and iterm2_backend.available():
        return iterm2_backend
    return wezterm
```

- **macOS + iTerm2 available → `iterm2_backend`.**
- **anything else → `wezterm`** — including a Mac *without* iTerm2 (the fallback lives
  entirely in that `and`).

`iterm2_backend.available()` requires all three: `Darwin`, `/Applications/iTerm.app`
exists, and `import iterm2` succeeds. `wezterm.available()` is just
`shutil.which("wezterm") is not None`. `_impl()` runs fresh on every call — no caching,
so installing a backend mid-session is picked up next call.

## The defining difference: partial layouts

Both backends tile a **full** layout as one maximized, split-pane window. They diverge
on **partial** layouts (a workspace with empty slots):

| | Full layout | Partial layout |
|---|---|---|
| **iTerm2 (macOS)** | one maximized split-pane window | **one window per filled slot** at its true screen rect; empty slots left as bare **desktop gaps** (`_build_gapped`) |
| **WezTerm (other)** | one split-pane window | **`compact()`** — empties dropped, survivors re-indexed and tiled; **no gap** |

Why: iTerm2 can place windows permission-free (via CoreGraphics geometry + its API), so
it preserves true geometry. WezTerm *cannot leave a hole* — every pane region must run a
program — and leaving a real gap would need the Accessibility grant WezTerm was chosen
to avoid. This is [ADR 0007](../decisions/0007-iterm2-backend-and-real-gap-layouts.md)
reversing [ADR 0005](../decisions/0005-combo-flip-and-partial-compaction.md)'s
compaction on macOS only.

## `iterm2_backend.py` — the iTerm2 Python API

### Async on its own event loop
The whole build tree is `async def` (awaiting the iterm2 lib throughout). `launch()`
creates a **fresh `asyncio` event loop** and runs `iterm2.run_until_complete(main,
retry=False)` — its own loop because the launcher runs on a pywebview GUI worker thread
with no ambient loop.

### Auth: Automation, and why `retry=False`
iTerm2's Python API gets its auth cookie through iTerm2's AppleScript automation
surface — so this needs **Automation** permission (not Accessibility). The lib's
built-in connect-retry **loops forever** on an auth denial, so it's disabled; the code
does its own waiting in `_ensure_running()` and, on failure, re-raises a `RuntimeError`
pointing at *System Settings › Privacy & Security › Automation*.

### Bringing iTerm2 up without a rogue window
- `_ensure_running()` — if iTerm2 isn't running, `open -g -a iTerm` (background), poll
  `pgrep -x iTerm2` up to ~8 s, then a 1.5 s settle for the API socket.
- It **deliberately never re-`open`s an already-running iTerm2** — activating a
  zero-window iTerm2 pops an empty default window.
- `cold = not _is_running()` is captured *before* ensuring — it gates stray-window
  cleanup.

### Spawning & tiling
- A **dynamic profile** is written first to
  `~/Library/Application Support/iTerm2/DynamicProfiles/terminal-launcher.json` (iTerm2
  hot-reloads that dir) — a dedicated One-Dark-ish / Menlo 13 profile that never touches
  the user's own profiles.
- Per-slot command + cwd ride in a write-only profile override
  (`LocalWriteOnlyProfile`): custom command `claude -n <name> --model <model>` (or the
  default shell for an empty slot), and a custom initial directory.
- **Full** → `_build_split`: create the window, then for each later slot
  `sessions[src].async_split_pane(vertical=(direction == "right"), …)` per
  `layouts.plan(layout, flip)`. **Note `"right"` → `vertical=True`.** Finally
  `async_set_frame(_screen_frame())` to maximize.
- **Partial** → `_build_gapped`: each filled slot is its own window placed at
  `_slot_rects(layout, flip)[slot.index]` (Cocoa coords, origin bottom-left; flip
  mirrors x). Empty slots simply aren't created.
- Screen size comes from **CoreGraphics via `ctypes`** (`CGMainDisplayID` /
  `CGDisplayBounds`) — permission-free, no AppleScript prompt — minus a 25 px menu bar.

### Stray-window cleanup
Only when `cold`, `_close_stray_default_window` closes a window **only** if it has
exactly one tab / one session whose name is a bare login shell
(`_SHELL_NAMES = {-zsh, zsh, -bash, …}`) — narrowly gated so it never kills a user's
real window.

## `wezterm.py` — driving `wezterm cli`

- **Compaction first:** `launch()` calls `model.compact(slots)` up front — WezTerm can't
  hold a gap, so empties are dropped and the layout becomes the tightest fit.
- **First pane, maximized:** `wezterm cli spawn --new-window` has no geometry flag, so
  the first pane is started via `open -na WezTerm --args start …` (or `wezterm-gui` on
  Windows) with `WEZTERM_CONFIG_FILE` pointed at the bundled `wezterm-maximize.lua`,
  whose `gui-startup` hook maximizes the window. Subsequent panes split into it:
  ```
  wezterm cli split-pane --pane-id <src> --<direction> --percent 50 --cwd <dir> -- <prog>
  ```
- **Program:** filled slot → `-- <claude> -n <name> --model <model>` (claude resolved to
  an absolute path, because a Dock-launched app hands WezTerm a minimal PATH); empty slot
  → `[]` (a login shell, which re-sources PATH).
- **Title:** `wezterm cli set-tab-title --pane-id <pid> <name>`.
- It re-declares its own `SPLIT_PLAN`/`_plan`/`FLIPPABLE` locally instead of importing
  `layouts.py` — a known drift risk on the [ADR 0007](../decisions/0007-iterm2-backend-and-real-gap-layouts.md)
  backlog.

## Identity injection (both backends)

Identity is three things — session **name/title**, and the Claude-side **`/color`**
prompt tint:

| | iTerm2 | WezTerm |
|---|---|---|
| Name/title | `session.async_set_name(name)` | `wezterm cli set-tab-title …` |
| `/color` text | `async_send_text("/color <c>")` | `send-text --pane-id … --no-paste "/color <c>"` |
| Submit | separate `async_send_text("\r")` | separate `send-text … "\r"` |
| Delays | 0.4 s after text, 0.2 s after CR | 0.4 s after text, 0.2 s after CR |

**The load-bearing gotcha, documented independently in both backends:** sending
`"/color x\r"` in one shot *types but does not submit* in Claude's TUI. You must send
the text, then a **lone carriage return as a separate call**. Collapsing them back to
one silently reintroduces the bug. See
[ADR 0002](../decisions/0002-identity-injection.md).

**The `colorDelay` path:** when `inject_color` is false, nothing is sent. WezTerm sleeps
`color_delay` once, then injects into each pane. iTerm2 is smarter — after the same
initial delay it also **waits for readiness per pane** (`_wait_ready` polls the pane's
screen text for markers like `"shift+tab"`, `"auto-accept"`, timing out at 12 s) so
`/color` lands in the prompt rather than a still-booting TUI.

## Gotchas worth remembering

- `vertical=(direction == "right")` — a `"right"` split is a *vertical* divider; easy to
  misread.
- iTerm2 leaves real desktop gaps; WezTerm compacts — same abstract layout, different
  physical result.
- `retry=False` is mandatory — the iterm2 lib's retry loops forever on auth denial.
- Split-plan logic exists in **three places** — canonically in `layouts.py`, imported by
  `iterm2_backend`, but re-declared in `wezterm.py`. Keep them in sync until the backlog
  item lands.
