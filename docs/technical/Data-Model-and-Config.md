# Data Model & Config

One JSON file — `workspaces.json` — is the single source of truth for panes,
workspaces, and settings. It's a **plain dict** end to end: there's no ORM or model
object; both front-ends mutate the dict and call `config.save`.

## Where the config lives

Resolution order (`config.default_config_path`, plus the CLI's `--config`):

1. `--config <path>` (CLI global flag) or the `TERMINAL_LAUNCHER_CONFIG` env var
2. `$XDG_CONFIG_HOME/terminal-launcher/workspaces.json`
3. `~/.config/terminal-launcher/workspaces.json`

`config.load()` backfills any missing top-level keys and `settings` sub-keys from
`DEFAULT_CONFIG`, so callers always see a complete shape. `config.save()` is **atomic**
— it writes a `.tmp` sibling and `replace()`s, so an interrupted write never truncates
your config.

## The schema

```jsonc
{
  "version": 1,
  "settings": {
    "defaultModel": "opus",   // global fallback model
    "injectColor": true,      // inject /color by default on launch
    "colorDelay": 1.5         // seconds to wait before injecting /color
  },
  "models": [                 // the model picker's options (id + label)
    { "id": "claude-fable-5", "label": "Fable 5" },
    { "id": "opus",           "label": "Opus 4.8" },
    { "id": "sonnet",         "label": "Sonnet 5" },
    { "id": "haiku",          "label": "Haiku 4.5" }
    // …
  ],
  "panes": {                  // registry, keyed by pane id (slug)
    "home": { "name": "Home", "color": "blue",  "target": "~",           "model": "sonnet" },
    "code": { "name": "Code", "color": "red",   "target": "~/code/app",  "model": "opus"   }
  },
  "workspaces": [             // saved compositions (ordered — order is the gallery order)
    {
      "name": "Docs",
      "layout": "split",      // single | split | combo | quad
      "flip": true,           // optional; stored only when true (split/combo only)
      "slots": [              // one entry per slot; null / omitted = empty
        { "pane": "home" },
        { "pane": "code", "model": "haiku" }   // model only when it OVERRIDES the pane default
      ]
    }
  ]
}
```

### Objects

| Object | Key fields |
|---|---|
| **settings** | `defaultModel`, `injectColor` (bool), `colorDelay` (seconds). |
| **model** | `id` (passed to `claude --model`), `label` (shown in the picker). |
| **pane** *(registry value)* | `name`, `color` (a named color), `target` (dir; `~`/`$VARS` allowed), `model` (default; optional). Keyed by a slug id. |
| **workspace** | `name`, `layout`, optional `flip`, `slots`. |
| **slot** | `{ "pane": <id> }`, optionally `+ "model"`; `null` or missing → empty. |

### Notable rules

- **`slots` length is advisory.** `resolve_workspace` always produces exactly
  `LAYOUT_CAPACITY[layout]` slots — extra entries are ignored, missing ones are padded
  as empty.
- **A slot's `model` is stored only when it overrides** the pane's own default. Inherited
  models are left off entirely (surfaced as the "Default" chip in the GUI). Same for
  `flip` — written only when `true`, so single/quad workspaces stay clean.
- **`color`** is a named value from `COLORS` — `blue, orange, red, purple, green, cyan,
  pink, gray` — each mapping to a hex (`color_hex`, default gray `#8a8a9a`).

## Resolution: workspace → ResolvedSlots

`model.resolve_workspace(config, ws)` turns a stored workspace into concrete slots:

```
ResolvedSlot(index, empty, pane_id, name, color, color_hex, target, model)
```

For each of the `LAYOUT_CAPACITY[layout]` positions:

- No pane assigned → `ResolvedSlot(index=i, empty=True)`.
- Assigned → look up the pane (dangling ref raises `CompositionError`), then fill
  `name`, `color`/`color_hex`, `target` (via `expand_target`: `~` then env vars), and
  `model` by precedence.

### Model precedence

```
slot override   →   pane default   →   global settings.defaultModel
```

`{ "pane": "code", "model": "haiku" }` runs haiku; `{ "pane": "code" }` runs the pane's
own `model` (`opus`); a pane with no `model` runs `settings.defaultModel`.

## Compaction: the second phase

`resolve_workspace` yields a **capacity-shaped** list (with empties marked).
`model.compact(slots)` is the optional second phase that produces a **density-shaped**
list — it drops empties, re-indexes survivors `0..n-1`, and returns
`(effective_layout, filled)` where the layout is the tightest fit for the filled count
(`COUNT_LAYOUT`: 1→single, 2→split, 3→combo, 4→quad).

Two phases, two consumers:

- **WezTerm** runs `compact` (it can't render a gap).
- **iTerm2** does *not* — it keeps the capacity-shaped slots and places each filled one
  at its true rect, leaving empties as desktop gaps.

## Two capacity tables — kept in lockstep by a test

Capacity is declared twice: `config.LAYOUT_CAPACITY` and `layouts.CAPACITY` (derived
from `SPLIT_PLAN` lengths). They must never drift — `tests/test_config.py` asserts
`LAYOUT_CAPACITY == CAPACITY` exactly to guard it. See
[Build, Packaging & Testing](Build-Packaging-Testing.md).
