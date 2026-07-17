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
  │  load/save/seed    resolve_workspace   split-plans          │
  │  defaults, colors  → ResolvedSlots     (dir/direction)      │
  │                    compact()           flip transform       │
  └───────────────────────────┬────────────────────────────────┘
                              │  backend.launch(layout, slots,
                              │    inject_color, workspace_name,
                              │    color_delay, flip)
                              ▼
  ┌────────────────────── Backend seam ────────────────────────┐
  │  backend.py   —   _impl() picks per platform:               │
  │     Darwin & iTerm2 installed → iterm2_backend              │
  │     otherwise (incl. macOS fallback) → wezterm              │
  └───────────────┬────────────────────────┬───────────────────┘
                  ▼                        ▼
        iterm2_backend.py             wezterm.py
        iTerm2 Python API             `wezterm cli`
        (async, native windows)       (subprocess)
                  \                    /
                   diag.py  ← one rotating log shared by every layer
```

Every backend satisfies the **same three-function contract** — `available()`,
`describe()`, `launch()` — so the layers above are backend-blind. Details in
[Backends](Backends.md).

## End-to-end: what `launch Docs` does

1. **Entry.** `python -m terminal_launcher` → `cli.main()` parses args and dispatches
   `cmd_launch` (`cli.py:148`). (The `.app` bundle enters via `app_main.py` straight
   into the GUI; the GUI's Launch button ends up in the same core calls.)
2. **Load + find.** `config.load(path)` reads `workspaces.json` and backfills defaults;
   `model.find_workspace(config, "Docs")` does a case-insensitive lookup.
3. **Resolve.** `model.resolve_workspace(config, ws)` returns a **capacity-shaped** list
   of `ResolvedSlot`s — always `LAYOUT_CAPACITY[layout]` of them, each either filled
   (final `name/color/target/model`, with **model precedence** applied: slot → pane →
   global) or marked `empty`.
4. **Hand off to the seam.** `backend.launch(layout, slots, inject_color=…,
   workspace_name=…, color_delay=…, flip=…)`. `backend._impl()` selects the platform
   backend fresh on every call.
5. **Backend realizes it.** Each backend turns the abstract layout into real windows
   using `layouts.plan(layout, flip)` — a list of `(direction, source-slot)` splits:
   - **iTerm2** — *full* layout → one maximized split-pane window; *partial* layout →
     one window per filled slot at its true screen rect, **empty slots left as desktop
     gaps** (`_build_gapped`).
   - **WezTerm** — `model.compact()` drops empties and re-indexes, then splits panes in
     one maximized window (no gaps — every WezTerm region must run a program).
6. **Apply identity.** Each filled pane gets its name/title set and — if `inject_color`
   — `/color <name>` typed in (as two separate sends; see [Backends](Backends.md)).
7. **Log throughout.** Every step, and any uncaught exception or forwarded WebView JS
   error, lands in the single `diag.py` rotating log.

## The key seams (where responsibilities are cut)

| Seam | Boundary | Why it's there |
|---|---|---|
| **Front-end ↔ core** | The plain `config` dict + `config.save`; `model.resolve_workspace`. | Lets the CLI and GUI stay thin and never diverge — one source of truth. |
| **Core ↔ backend** | `backend.launch(layout, slots, …)` with `ResolvedSlot`s. | The core is platform-agnostic; swapping terminals is one new module ([ADR 0001](../decisions/0001-terminal-layer-and-core.md)). |
| **Abstract layout ↔ geometry** | `layouts.plan(layout, flip)` → `(direction, src)` steps. | Terminal-agnostic, unit-tested; shared by both backends ([ADR 0007](../decisions/0007-iterm2-backend-and-real-gap-layouts.md)). |
| **Resolve ↔ compact** | `resolve_workspace` (capacity-shaped) then `compact` (density-shaped). | Two phases: fill/mark empties, then decide whether to drop them — a per-backend choice. |

## Why the design looks like this

The whole shape follows from the ADRs:

- A **thin core behind a backend seam** ([0001](../decisions/0001-terminal-layer-and-core.md))
  is what let the macOS terminal layer swap from WezTerm to iTerm2 as a *single new
  module* ([0007](../decisions/0007-iterm2-backend-and-real-gap-layouts.md)) without
  touching the core or front-ends.
- **Identity injection** targets a specific pane id/session, so it needs no
  Accessibility permission ([0002](../decisions/0002-identity-injection.md)).
- The **visual composer is a fleeting pywebview window** over the same config, not a
  server ([0003](../decisions/0003-visual-composer-pywebview.md)).
- **Partial layouts** are handled *in-engine* — compaction on WezTerm, real gaps on
  iTerm2 ([0005](../decisions/0005-combo-flip-and-partial-compaction.md),
  [0007](../decisions/0007-iterm2-backend-and-real-gap-layouts.md)) — so the OS-window
  placement layer ([0004](../decisions/0004-heterogeneous-panes-and-window-placement.md),
  still *proposed*) is needed only for future non-terminal panes.

For the full decision history and current live-vs-deferred state, read
[`../decisions/`](../decisions/).
