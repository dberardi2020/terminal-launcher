# Tech Stack

A deliberately small stack. The core is **stdlib-only**; every third-party dependency
buys exactly one capability and is isolated behind a seam so the rest of the code
doesn't depend on it.

## Language & runtime

- **Python 3.10+** — uses `from __future__ import annotations`; developed on 3.14.
- **Version** — `terminal_launcher.__version__ = "1.2.0"` (`__init__.py`), mirrored in
  the py2app plist `CFBundleShortVersionString`.

## Dependencies (`requirements.txt`)

| Package | Version | Buys | Needed for |
|---|---|---|---|
| `pywebview` | `>=6.2` | A native window hosting local HTML/JS, bridged to Python | The visual composer (`gui.py`) |
| `iterm2` | `>=2.7` | The iTerm2 Python API (async) | The macOS terminal backend |

Everything else is the **standard library**: `argparse`, `json`, `pathlib`,
`subprocess`, `asyncio`, `ctypes`, `logging`, `shutil`, `shlex`, `platform`,
`functools`.

**The CLI and the WezTerm backend are stdlib-only** — `iterm2` and `pywebview` are both
imported *lazily inside functions*, so a machine that only uses the CLI + WezTerm never
needs them installed.

## What each third-party piece does — and why it

### pywebview — the visual composer

Hosts `web/builder.html` (a single self-contained HTML/CSS/JS file) in the OS-native
WebView (WKWebView on macOS, WebView2 on Windows) and exposes a Python object as
`window.pywebview.api.*`. **No web server, no persistent process.**

*Why:* the composer is meant to be *fleeting* — appear, compose, launch, vanish. A
long-running localhost server contradicts that, and heavier native toolkits
(SwiftUI/Avalonia/Tauri) would mean a UI rewrite or a new build toolchain. pywebview
reuses the existing HTML UI and the Python core with no new language. See
[ADR 0003](../decisions/0003-visual-composer-pywebview.md). The bridge is detailed in
[Module Reference](Module-Reference.md#guipy).

### iterm2 — the macOS terminal backend

The official async Python API for iTerm2. `iterm2_backend.py` holds direct `Session`
references to exactly the panes it creates, giving unambiguous per-pane control and
native windows.

*Why:* WezTerm on macOS couldn't deliver deterministic placement of named panes
(`--class` is X11/Wayland-only; its multi-window model made "control *this* window"
ambiguous). iTerm2's API fixed that. Auth is via **Automation** permission (an
AppleScript Apple Event obtains the API cookie) — lighter than the Accessibility grant
an arbitrary-window placer would need. See
[ADR 0007](../decisions/0007-iterm2-backend-and-real-gap-layouts.md).

### `wezterm cli` — the non-macOS terminal backend

Not a Python dependency — an **external binary** driven via `subprocess`. `wezterm.py`
shells out to `wezterm cli spawn` / `split-pane` / `set-tab-title` / `send-text`.

*Why:* `wezterm cli` returns pane-ids, so scripted tiling is exact, and
`send-text --pane-id` targets a pane without focus or Accessibility. It's identical on
macOS and Windows, giving cross-platform parity by construction. See
[ADR 0001](../decisions/0001-terminal-layer-and-core.md).

### Claude Code (`claude`) — the payload

Not a dependency of the tool, but what every filled pane runs:
`claude -n <name> --model <model>`. Both backends resolve it to an absolute path
(`shutil.which("claude")`) because a Dock-launched `.app` inherits a minimal PATH.

## Build & test tooling

- **py2app** — builds the macOS Dock `.app` (`setup.py`). Dev/packaging only. See
  [Build, Packaging & Testing](Build-Packaging-Testing.md).
- **pytest** — unit tests for the pure core (`layouts`, `model`, `config`). No terminal
  or GUI is exercised in tests.
- **docs render** — `docs/render.py` (stdlib-only) renders the Markdown docs to their
  paired HTML; there's no docs build system beyond it.

## The dependency-isolation rule

The stack stays swappable because every external piece sits behind a seam:

- `iterm2` and `wezterm` are reached **only** through `backend.py`'s three-function
  contract — the core and front-ends import neither.
- `pywebview` is imported **only** inside `gui.py` (and lazily), so the CLI never loads
  it.
- `iterm2` is imported lazily inside `iterm2_backend` functions — which is also why
  `setup.py` must force it into the py2app graph explicitly.
