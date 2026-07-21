# Terminal Launcher — Technical docs

Documentation for **developers** working on the code. Assumes you've skimmed the
[Product docs](../product/README.md) for the vocabulary (Pane · Layout · Workspace).

## Start here

| Doc | Read it for |
|---|---|
| [Architecture](Architecture.md) | The layered design and the end-to-end flow from `launch Docs` to tiled windows. |
| [Tech Stack](Tech-Stack.md) | The dependencies — stdlib core, pywebview, iterm2 API, `wt` + Win32, py2app/PyInstaller, pytest — and *why* each. |
| [Module Reference](Module-Reference.md) | Every module: responsibility, key functions, cross-calls. |
| [Backends](Backends.md) | The terminal-backend abstraction — the heart of the system. |
| [Data Model & Config](Data-Model-and-Config.md) | The `workspaces.json` schema, resolution order, and model precedence. |
| [Build, Packaging & Testing](Build-Packaging-Testing.md) | The py2app `.app` and PyInstaller `.exe` bundles, asset loading, entitlements, and the test suite. |

## The shape, at a glance

~2,000 lines of Python across 11 modules, plus one self-contained HTML/JS GUI file.
Layered: **front-ends** → **core** → **backend seam** → **terminal backends**.

```
bin/terminal-launcher          # executable entry point (symlink onto PATH)
app_main.py                    # .app / Dock entry → straight to GUI
terminal_launcher/
  __main__.py  __init__.py     # CLI entry (python -m …) · version
  cli.py                       # argparse + interactive composer wizard
  gui.py                       # visual composer (pywebview) + JS↔Python bridge
  web/builder.html             # the entire GUI front-end (inline HTML/CSS/JS)
  config.py                    # config load/save/defaults, color map
  model.py                     # workspace → concrete ResolvedSlots
  layouts.py                   # split-plans + capacity (terminal-agnostic; unit-tested)
  backend.py                   # selects the terminal backend per platform
  iterm2_backend.py            # macOS backend — iTerm2 Python API
  windows_terminal_backend.py  # Windows backend — `wt` + Win32 (ctypes)
  diag.py                      # rotating log shared by CLI + GUI + backends
tests/                         # pytest: layouts, model, config
packaging/                     # py2app macOS .app + PyInstaller Windows .exe
docs/                          # this suite + concept.md + decisions/ (ADRs)
```

## The two invariants worth knowing first

- **The config is a dumb JSON dict.** There's no ORM or model object for panes and
  workspaces — every mutation in both front-ends is "change the plain dict, then
  `config.save(path, config)`". See [Data Model & Config](Data-Model-and-Config.md).
- **Neither front-end knows which terminal it's driving.** They call
  `backend.launch(...)`; the platform split (iTerm2 vs Windows Terminal) lives entirely
  behind that seam. See [Backends](Backends.md).

## Deeper references

- [`../decisions/`](../decisions/) — the ADRs: *why* each choice was made (start with
  [0001](../decisions/0001-terminal-layer-and-core.md) and
  [0007](../decisions/0007-iterm2-backend-and-real-gap-layouts.md), and
  [0008](../decisions/0008-one-window-per-pane-and-windows-terminal-backend.md)).
- [`../concept.md`](../concept.md) — the as-built product concept.
