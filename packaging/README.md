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

**Icon:** PyInstaller wants a Windows `.ico`. The spec uses `windows/app.ico` if present,
otherwise it builds without an icon. Generate one from `icon.png`, e.g. with ImageMagick:

```powershell
magick packaging\icon.png -define icon:auto-resize=256,128,64,48,32,16 packaging\windows\app.ico
```
