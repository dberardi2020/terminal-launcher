# Packaging

Build the macOS Dock app (`Terminal Launcher.app`) with **py2app**.

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
