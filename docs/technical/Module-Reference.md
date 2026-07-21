# Module Reference

A map of every module: what it owns, its key surface, and how it connects. Deep dives
live in [Backends](Backends.md) and [Data Model & Config](Data-Model-and-Config.md);
this is the index.

Dependency direction: **front-ends → core → backend seam → backends**, with `diag`
underneath everything.

---

## Core

### `config.py`
**Owns** the single JSON config: load, save, seed, defaults, and the color map.

- `default_config_path()` — resolution order: `TERMINAL_LAUNCHER_CONFIG` env →
  `$XDG_CONFIG_HOME/terminal-launcher/workspaces.json` → `~/.config/…`.
- `load(path)` — reads UTF-8 JSON and backfills missing `DEFAULT_CONFIG` keys /
  `settings` sub-keys (top-level defaults are deep-copied to avoid aliasing).
- `save(path, config)` — **atomic**: writes `*.tmp`, then `replace()` so a crash never
  truncates the config.
- `seed_from_example(path)` / `example_config_path()` — create a starter config from
  the bundled `workspaces.example.json`.
- `color_hex(name)` — named color → hex, default gray `#8a8a9a`.
- **Constants:** `COLORS` (8 named→hex), `LAYOUT_CAPACITY` `{single:1, split:2,
  combo:3, quad:4}`, `DEFAULT_CONFIG`. Full schema in
  [Data Model & Config](Data-Model-and-Config.md).

*Imports:* stdlib only. *Consumed by:* both front-ends, `model.py`.

### `model.py`
**Owns** the platform-agnostic composition engine: workspace → concrete slots.

- `@dataclass ResolvedSlot` — `index, empty, pane_id, name, color, color_hex, target,
  model`.
- `resolve_workspace(config, ws)` — returns exactly `LAYOUT_CAPACITY[layout]` slots,
  each filled or `empty`. Applies **model precedence** slot → pane → global; expands
  `target`. Raises `CompositionError` on unknown layout or dangling pane ref.
- `expand_target(raw)` — `expanduser` then `expandvars`, normalized.
- `find_workspace(config, name)` — case-insensitive, trimmed lookup.

*Imports:* `LAYOUT_CAPACITY`, `color_hex` from `config`. *Consumed by:* both front-ends,
both backends (via the resolved slots).

### `layouts.py`
**Owns** the terminal-agnostic split-plans and the flip transform. Unit-tested; the
intended single source of truth for geometry.

- `plan(layout, flip=False)` — returns a list of `(direction, source-slot-index)` steps
  for each slot after the first. Flip swaps `right↔left` for split/combo only
  (`bottom` untouched).
- **Constants:** `SPLIT_PLAN` (`split:[("right",0)]`, `combo:[("right",0),("bottom",1)]`,
  `quad:[("right",0),("bottom",0),("bottom",1)]`), `CAPACITY`, `FLIPPABLE={split,combo}`.

*Imports:* none. *Consumed by:* both backends import `FLIPPABLE` (for the flip mirror);
`CAPACITY` derives from `SPLIT_PLAN` and is cross-checked against `config.LAYOUT_CAPACITY`
in the tests. `plan()`/`SPLIT_PLAN` are no longer on the launch path — the native backends
place by slot *rectangle*, not split direction.

---

## Backend seam

### `backend.py`
**Owns** platform selection — a pure router, no terminal logic.

- `_impl()` — `iterm2_backend.available()` (macOS + iTerm2) → `iterm2_backend`;
  `windows_terminal_backend.available()` (Windows + `wt`) → that; else `None` (no native
  backend — `available()` is False, `launch()` raises). Re-evaluated on every call, no
  caching.
- Re-exports the contract: `available()`, `describe(layout, slots, flip)`,
  `launch(layout, slots, inject_color, workspace_name, color_delay, flip)`, plus
  `name()` and `install_hint()`.

### `iterm2_backend.py` · `windows_terminal_backend.py`
The two native terminal backends behind the contract — full treatment in
[Backends](Backends.md). Both realize the **same** model: one OS window per filled slot
placed at its rect, with real desktop gaps for empties (no compaction). In brief:

- **`iterm2_backend.py`** — async, drives the iTerm2 Python API on its own event loop; a
  window per slot, `async_set_frame` to the Cocoa rect. Auth via Automation permission.
- **`windows_terminal_backend.py`** — pure `ctypes`; spawns `wt -w new` per slot, finds the
  window by class-name diff, and `SetWindowPos`es it to the Win32 rect (DPI + DWM
  compensation). `/color` via focus + clipboard paste (no `send-text` equivalent). No
  permission prompt.

---

## Front-ends

### `cli.py`
**Owns** the argparse surface and the interactive composer wizard.

- `build_parser()` — verbs: `list`, `panes`, `preview <name>`, `launch <name>
  [--dry-run] [--inject-color]`, `new`, `edit <name>`, `delete <name>`, `pane-new`,
  `gui`, `init`, `logs [--lines]`, plus a global `--config`.
- `main()` — resolves the config path, chooses a load policy per verb (`_load_or_die`
  vs `_load_or_seed` vs empty for `init`), dispatches, returns `130` on
  `KeyboardInterrupt`.
- **Wizard:** `_compose_workspace(config, existing=None)` drives layout choice →
  per-slot `_choose_pane` / `_choose_model` → optional flip (split/combo only).
  `_interactive_pane(config)` builds a pane. Every write-back is "mutate `config`, then
  `config.save`".

*Note:* a slot stores `model` only when it **overrides** the pane default — inherited
models are left off (the "Default" chip).

### `gui.py`
<a id="guipy"></a>**Owns** the pywebview window and the JS↔Python bridge.

- `run(path)` — lazily imports `webview`, calls `diag.setup()` and
  `_inherit_login_path()` (merges the login-shell PATH so a Dock-launched `.app` can
  find `claude`/`iterm2`; a no-op on Windows), reads `web/builder.html` off disk, and
  `create_window(..., js_api=api, maximized=True)`.
- `class Api` — the bridge, exposed as `window.pywebview.api.*`. Every public method is
  wrapped in an exception tracer (`gui.py:71`) because pywebview otherwise swallows
  errors into silently-rejected JS promises. Methods: `get_state`, `save_workspace`,
  `delete_workspace`, `duplicate_workspace`, `move_workspace`, `reorder_workspace`,
  `save_pane`, `delete_pane`, `pick_directory`, `launch`, `log_client`,
  `get_diagnostics`, `export_logs`.
- `_normalize_slots()` — the wire-format adapter between the JS slot list and the
  on-disk shape (pads/trims to capacity, strips inherited models).
- **Launch is threaded:** validation is synchronous (bad input returns to JS instantly),
  but `backend.launch(...)` runs on a daemon thread; on a fleeting launch it ends with
  `os._exit(0)` (pywebview's `destroy()` is unreliable from a non-managed thread). See
  [ADR 0003](../decisions/0003-visual-composer-pywebview.md).

### `web/builder.html`
The entire GUI front-end — one self-contained file (inline HTML/CSS/JS, no external
assets). A launchpad of workspace cards over a live composer; the slot editor is an
inline side panel (`sideMode` ∈ `hint|slot|panes|paneform`). `const api = () =>
window.pywebview.api` is the single bridge accessor. JS errors (`window.onerror`,
`unhandledrejection`, `console.error`) are forwarded to the Python log via
`api.log_client`.

---

## Entry points

| File | Door | Does |
|---|---|---|
| `bin/terminal-launcher` | shell | Executable symlinked onto `PATH`. |
| `__main__.py` | CLI | `python -m terminal_launcher` → `cli.main()`. |
| `app_main.py` | `.app` | The py2app entry — `run()` straight into the GUI, bypassing argparse. |
| `__init__.py` | — | Package docstring + `__version__ = "1.4.0"`. |

---

## Diagnostics

### `diag.py`
**Owns** the single rotating log every layer writes to:
`~/.config/terminal-launcher/terminal-launcher.log`.

- `setup()` — idempotent; attaches a `RotatingFileHandler` (512 KB × 2) + a stderr
  handler, and installs a `sys.excepthook` that logs uncaught exceptions as `UNCAUGHT`.
- `get_logger()` / `log_path()` / `read_tail(n=200)`.

Crucially, WebView JS errors are forwarded here over the bridge (`Api.log_client`), so a
composer bug leaves a record instead of vanishing into the WebView console. Surfaced via
the `logs` CLI verb and the GUI's reveal-log button.
