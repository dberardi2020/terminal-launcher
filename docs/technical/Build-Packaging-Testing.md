# Build, Packaging & Testing

## Running from source

No build step. Symlink the entry point onto `PATH`:

```sh
ln -s "$(pwd)/bin/terminal-launcher" ~/.local/bin/terminal-launcher
```

`python -m terminal_launcher` works too (via `__main__.py`) — on Windows,
`py -m terminal_launcher …`. The CLI and the Windows Terminal backend are stdlib-only;
install `requirements.txt` only if you need the visual composer (`pywebview`) or the
iTerm2 backend (`iterm2`).

## macOS Dock app (py2app)

`setup.py` builds a double-clickable `.app` around the visual composer:

```sh
source .venv/bin/activate
pip install -r requirements.txt py2app     # first time
python setup.py py2app                     # → dist/Terminal Launcher.app
```

Drag `dist/Terminal Launcher.app` to `/Applications`. Double-clicking opens the composer
maximized (via `app_main.py` → `gui.run()`); a fleeting launch exits the app behind you.
`build/` and `dist/` are git-ignored throwaways.

### Two things the bundle gets right (and why they're fragile)

1. **`terminal_launcher` is shipped unzipped.** `setup.py` lists it under `packages` so
   py2app copies it as a real directory. The launcher reads `web/builder.html` **off disk
   via `__file__`** — a zipped egg would break it. If you ever see the GUI fail to load its
   HTML in a bundle, this is why.
2. **`iterm2` is force-listed under `packages`.** It's imported lazily inside functions,
   so py2app's static import graph misses it; naming it explicitly pulls it in (and its
   deps — websockets, protobuf).

### The plist entitlements (`setup.py`)

| Key | Value | Why |
|---|---|---|
| `CFBundleIdentifier` | `com.dberardi.terminal-launcher` | Bundle identity. |
| `CFBundleShortVersionString` | `1.2.0` | Mirrors `__version__`. |
| `LSUIElement` | `False` | A normal Dock app with a window, not a background agent. |
| `NSHighResolutionCapable` | `True` | Retina. |
| `NSAppleEventsUsageDescription` | *(consent string)* | **Required** so macOS shows the Automation prompt — iTerm2's API obtains its auth cookie via an Apple Event; without this key macOS silently denies it. |

### PATH inheritance

A Dock/Finder launch gets a stripped PATH, so `gui.run()` calls `_inherit_login_path()`
— it runs the login shell (`$SHELL -lic 'echo $PATH'`) and merges in the user/Homebrew
bins so `claude` and `iterm2` resolve. (`iterm2_backend.py` additionally resolves `claude`
to an absolute path for the same reason.) It is a no-op on Windows, where `wt`/`claude`
resolve normally.

### TCC persistence caveat

An **unsigned** py2app bundle may re-prompt for Automation after each rebuild (its code
signature changes). Acceptable for a personal tool; ad-hoc signing would stabilize it
(open item in [ADR 0007](../decisions/0007-iterm2-backend-and-real-gap-layouts.md)).

### Icon

`packaging/icon.png` (1024²) is the master; `packaging/icon.icns` is the bundled icon
referenced by `setup.py`. Regenerate the master with `python packaging/make-icon.py`,
then rebuild the `.icns` (the `sips`/`iconutil` recipe is in
[`packaging/README.md`](../../packaging/README.md)).

## Windows (.exe via PyInstaller)

`packaging/windows/terminal-launcher.spec` builds a windowed `.exe` around the visual
composer, mirroring what py2app does on macOS. From the repo root:

```powershell
py -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt pyinstaller           # first time
pyinstaller packaging\windows\terminal-launcher.spec  # -> dist\Terminal Launcher\
```

The spec uses `collect_all('webview')` to pull pywebview's WebView2 loader and data files
into the bundle, and ships `terminal_launcher/web/` as data (the GUI reads `builder.html`
off disk via `__file__`). `build/` and `dist/` are git-ignored throwaways.

**No bundle is needed to run it.** The CLI and the Windows Terminal backend are
stdlib-only, so `py -m terminal_launcher launch <ws>` works with nothing installed. For a
double-clickable GUI *without* building an `.exe`, run
`packaging/windows/install-shortcut.ps1` — it drops a **Start Menu** entry (icon and all)
running `pythonw -m terminal_launcher gui`, no console window; `terminal-launcher.cmd`
beside it does the same from a double-click. Installing `pywebview` is the only
requirement for the GUI.

*Icon:* PyInstaller wants a Windows `.ico`; the spec uses `packaging/windows/app.ico` if
present and omits the icon otherwise (generate one from `packaging/icon.png` when wanted).

## Testing

`pytest` covers the **pure core** — no terminal, GUI, or subprocess is exercised. Run:

```sh
pytest
```

| File | Covers |
|---|---|
| `tests/test_layouts.py` | `SPLIT_PLAN`/`CAPACITY`/`plan()` — the split geometry, flip mirroring (`right→left`, `bottom` untouched), flip is a no-op for single/quad, unknown layout → empty plan. |
| `tests/test_model.py` | `resolve_workspace` (fill + mark empties, pad missing slots, model precedence, dangling-pane/unknown-layout errors), `expand_target`, `find_workspace`. |
| `tests/test_config.py` | `color_hex` for every named color, the atomic `save`/`load` round-trip, and — critically — **`LAYOUT_CAPACITY == CAPACITY`** so the two capacity tables can't drift. |

### What's not covered

The backends (`iterm2_backend`, `windows_terminal_backend`), the GUI bridge (`gui.py`),
and `cli.py`'s wizard have no automated tests — they're I/O- and permission-bound.
iTerm2's API does,
however, make **self-validation by read-back** possible (a launch can be verified via
the API + `screencapture` with no human), which is a future direction noted in
[ADR 0007](../decisions/0007-iterm2-backend-and-real-gap-layouts.md).

For the Windows backend, an interactive **manual smoke-test checklist** lives at
[`windows-smoke-test.html`](windows-smoke-test.html) — open it in a browser and tick
through a real launch (dry-run → single/split/quad/flip → `/color` paste → clipboard
restore → diag log). It's a single-format interactive page (no Markdown twin).
