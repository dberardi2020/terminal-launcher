# Packaging

Double-clickable builds of the visual composer: **py2app** on macOS, **PyInstaller** on
Windows. Neither is needed to *use* the tool — the CLI (`terminal-launcher` /
`py -m terminal_launcher`) runs from source with no build.

## macOS (.app via py2app)

Build the macOS Dock app (`Terminal Launcher.app`):

## Build

```sh
source .venv/bin/activate
pip install -r requirements.txt py2app        # first time
python setup.py py2app                         # → dist/Terminal Launcher.app
```

Then drag `dist/Terminal Launcher.app` to `/Applications`. Double-clicking it opens
the visual composer maximized; a fleeting launch exits the app behind you.

`build/` and `dist/` are throwaway (git-ignored) — the app is rebuilt on demand, not
kept in the (synced) project folder.

## Icon

`icon.png` (1024²) is the master; `icon.icns` is the bundled icon (referenced by
`setup.py`). Regenerate the master with `python packaging/make-icon.py`, then rebuild
`icon.icns`:

```sh
mkdir icon.iconset
for s in 16 32 128 256 512; do
  sips -z $s   $s   packaging/icon.png --out icon.iconset/icon_${s}x${s}.png
  sips -z $((s*2)) $((s*2)) packaging/icon.png --out icon.iconset/icon_${s}x${s}@2x.png
done
iconutil -c icns icon.iconset -o packaging/icon.icns && rm -rf icon.iconset
```

## Windows (.exe via PyInstaller)

Build a windowed `.exe` around the composer from the **repo root**:

```powershell
py -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt pyinstaller
pyinstaller packaging\windows\terminal-launcher.spec   # -> dist\Terminal Launcher\
```

`windows/terminal-launcher.spec` collects pywebview's WebView2 loader and ships
`terminal_launcher/web/` as data. `build/` and `dist/` are throwaway (git-ignored).

To run the GUI **without** building an `.exe`, double-click
`windows/terminal-launcher.cmd` (it runs `pythonw -m terminal_launcher gui`, no console
window); that only needs Python + `pywebview`. The CLI itself
(`py -m terminal_launcher …`) needs nothing beyond the standard library.

### Start Menu shortcut (no build at all)

The lightest way to get a launchable entry on Windows — a Start Menu shortcut that runs
the composer with `pythonw` (no console window) straight from this checkout:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\install-shortcut.ps1
powershell -ExecutionPolicy Bypass -File packaging\windows\install-shortcut.ps1 -Uninstall
```

It resolves `pythonw.exe` via the `py` launcher and sets the working directory to the
checkout (so `-m terminal_launcher` resolves). Needs only Python + `pywebview` — no
PyInstaller. Verified on Windows 11.

The icon is **copied to `%LOCALAPPDATA%\Terminal Launcher\app.ico`** and the shortcut
points there rather than into the checkout. Two reasons: the Start Menu entry keeps its
icon if the checkout ever moves, and Windows' shell icon cache will serve a *stale* icon
for a path it has already seen — even after the file changes — so installing to a fresh
path is the reliable way to make a new icon actually show up. `-Uninstall` removes it.

**Icon:** `windows/app.ico` is committed (multi-size, 16–256 px) and used by both the
shortcut and the PyInstaller spec. Regenerate it from the master `icon.png` with Pillow:

```powershell
py -c "from PIL import Image; im=Image.open('packaging/icon.png').convert('RGBA'); im.save('packaging/windows/app.ico', sizes=[(s,s) for s in (16,24,32,48,64,128,256)])"
```
