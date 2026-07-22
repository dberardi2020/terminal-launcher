# Architecture

Terminal Launcher is a **thin Python core** with two interchangeable **front-ends** on
top and two interchangeable **terminal backends** underneath, joined by a single
platform-agnostic seam. The core never touches a terminal directly and never does
window math; the backends never touch the config.

## The layers

```
  ┌──────────────────────── Front-ends ────────────────────────┐
  │   cli.py  (argparse + wizard)      gui.py  (pywebview)      │
  │        headless / scriptable       web/builder.html         │
  └───────────────┬────────────────────────┬───────────────────┘
                  │   both mutate the same plain config dict,
                  │   then config.save(path, config)
                  ▼                        ▼
  ┌──────────────────────────── Core ──────────────────────────┐
  │  config.py         model.py            layouts.py           │
  │  load/save/seed    resolve_workspace   split-plans +        │
  │  defaults, colors  → ResolvedSlots     capacity, flip       │
  └───────────────────────────┬────────────────────────────────┘
                              │  backend.launch(layout, slots,
                              │    inject_color, workspace_name,
                              │    color_delay, flip)
                              ▼
  ┌────────────────────── Backend seam ────────────────────────┐
  │  backend.py   —   _impl() picks per platform:               │
  │     Darwin  → iterm2_backend                                │
  │     Windows → windows_terminal_backend                      │
  │     else    → none (available() = False)                    │
  └───────────────┬────────────────────────┬───────────────────┘
                  ▼                        ▼
      iterm2_backend.py          windows_terminal_backend.py
      iTerm2 Python API          `wt` + Win32 (ctypes)
      (async, native windows)    (spawn, SetWindowPos)
                  \                    /
                   diag.py  ← one rotating log shared by every layer
```

Every backend satisfies the **same three-function contract** — `available()`,
`describe()`, `launch()` — so the layers above are backend-blind. Both realize one
uniform model: **one real OS window per pane, placed by geometry, with real desktop gaps
for empty slots.** Details in [Backends](backends.md).

## End-to-end: what `launch Docs` does

1. **Entry.** `python -m terminal_launcher` → `cli.main()` parses args and dispatches
   `cmd_launch`. (The `.app`/`.exe` bundle enters via `app_main.py` straight into the GUI;
   the GUI's Launch button ends up in the same core calls.)
2. **Load + find.** `config.load(path)` reads `workspaces.json` and backfills defaults;
   `model.find_workspace(config, "Docs")` does a case-insensitive lookup.
3. **Resolve.** `model.resolve_workspace(config, ws)` returns a **capacity-shaped** list
   of `ResolvedSlot`s — always `LAYOUT_CAPACITY[layout]` of them, each either filled
   (final `name/color/target/model`, with **model precedence** applied: slot → pane →
   global) or marked `empty`.
4. **Hand off to the seam.** `backend.launch(layout, slots, …)`. `backend._impl()`
   selects the platform backend fresh on every call (`Darwin` → iTerm2, `Windows` →
   Windows Terminal).
5. **Backend realizes it.** Each backend places one real OS window per *filled* slot at
   its slot rectangle (`_slot_rects(layout, flip)`); empty slots are simply not spawned,
   leaving real desktop gaps. A full quad is four windows in four quadrants, not one
   split-pane window.
   - **iTerm2** — creates a window per slot via the Python API, `async_set_frame` to the
     Cocoa rect.
   - **Windows Terminal** — spawns a `wt` window per slot, finds it, `SetWindowPos` to the
     Win32 rect (with DPI + DWM-border compensation).
6. **Apply identity.** Each window's title/name is set and — if `inject_color` — `/color
   <name>` is delivered (iTerm2: `send-text`; Windows Terminal: focus + clipboard paste; see
   [Backends](backends.md)).
7. **Log throughout.** Every step, and any uncaught exception or forwarded WebView JS
   error, lands in the single `diag.py` rotating log.

## The key seams (where responsibilities are cut)

| Seam | Boundary | Why it's there |
|---|---|---|
| **Front-end ↔ core** | The plain `config` dict + `config.save`; `model.resolve_workspace`. | Lets the CLI and GUI stay thin and never diverge — one source of truth. |
| **Core ↔ backend** | `backend.launch(layout, slots, …)` with `ResolvedSlot`s. | The core is platform-agnostic; a new terminal is one new module ([ADR 0001](../decisions/0001-terminal-layer-and-core.md)). |
| **Abstract layout ↔ geometry** | Each backend's `_slot_rects(layout, flip)` → per-slot rectangles from the OS work area. | Terminal-agnostic placement; the same logical layout on both platforms ([ADR 0008](../decisions/0008-one-window-per-pane-and-windows-terminal-backend.md)). |

## Why the design looks like this

The shape follows from the ADRs:

- A **thin core behind a backend seam** ([0001](../decisions/0001-terminal-layer-and-core.md))
  is what let the macOS layer swap to iTerm2 ([0007](../decisions/0007-iterm2-backend-and-real-gap-layouts.md))
  and a native Windows Terminal backend be added
  ([0008](../decisions/0008-one-window-per-pane-and-windows-terminal-backend.md)) as single new
  modules, without touching the core or front-ends.
- **One window per pane, self-placed by geometry** on both platforms
  ([0008](../decisions/0008-one-window-per-pane-and-windows-terminal-backend.md)): neither OS
  lets you invoke native snapping programmatically without synthetic input or the
  Accessibility permission, so each backend places its own windows at the work-area
  rectangles — deterministic and permission-light.
- **Identity injection** targets a specific window/session, so on macOS it needs no
  Accessibility permission ([0002](../decisions/0002-identity-injection.md)); on Windows it
  focuses the window and pastes via the clipboard (no `send-text` equivalent exists for `wt`).
- The **visual composer is a fleeting pywebview window** over the same config, not a
  server ([0003](../decisions/0003-visual-composer-pywebview.md)).

For the full decision history and current live-vs-deferred state, read
[`../decisions/`](../decisions/).
