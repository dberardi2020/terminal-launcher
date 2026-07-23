# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Terminal Launcher visual composer on Windows.
#
# Build from the REPO ROOT:
#     pyinstaller packaging\windows\terminal-launcher.spec      # -> dist\Terminal Launcher\
#
# Mirrors what setup.py (py2app) does on macOS: a windowed app around app_main.py.
# Requires PyInstaller 6.x. (On 5.x, PYZ takes (a.pure, a.zipped_data).)
import os
from PyInstaller.utils.hooks import collect_all

# pywebview ships the WebView2 loader + data files; collect_all pulls them in so the
# bundled GUI can create its native window.
datas, binaries, hiddenimports = collect_all('webview')

# The GUI reads terminal_launcher/web/builder.html off disk via __file__, so it must be
# shipped as data (an importable package alone doesn't carry non-.py files reliably).
# Source is under src/ (src layout); the in-bundle destination stays terminal_launcher/web
# so the runtime __file__ path is unchanged.
datas += [('src/terminal_launcher/web', 'terminal_launcher/web')]

# Optional icon — PyInstaller needs a Windows .ico. Use it if present, else no icon.
_icon = os.path.join('packaging', 'windows', 'app.ico')
icon = _icon if os.path.exists(_icon) else None

a = Analysis(
    ['app_main.py'],
    pathex=['src'],   # src layout: terminal_launcher lives under src/
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Terminal Launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # windowed: no console window behind the GUI
    disable_windowed_traceback=False,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Terminal Launcher',
)
