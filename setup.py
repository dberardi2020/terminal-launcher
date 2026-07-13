"""macOS .app packaging for Terminal Launcher's visual composer (py2app).

    python setup.py py2app        # builds dist/Terminal Launcher.app

`terminal_launcher` is listed under `packages` so py2app copies it unzipped —
the launcher reads web/builder.html and assets/wezterm-maximize.lua off disk via
__file__, which only works when the package is a real directory in the bundle.
"""
from setuptools import setup

setup(
    app=["app_main.py"],
    name="Terminal Launcher",
    options={"py2app": {
        "argv_emulation": False,
        "iconfile": "packaging/icon.icns",
        "packages": ["terminal_launcher", "webview"],
        "plist": {
            "CFBundleName": "Terminal Launcher",
            "CFBundleDisplayName": "Terminal Launcher",
            "CFBundleIdentifier": "com.dberardi.terminal-launcher",
            "CFBundleShortVersionString": "1.0.0",
            "LSUIElement": False,
            "NSHighResolutionCapable": True,
        },
    }},
    setup_requires=["py2app"],
)
