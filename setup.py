"""macOS .app packaging for Terminal Launcher's visual composer (py2app).

    python setup.py py2app        # builds dist/Terminal Launcher.app

`terminal_launcher` is listed under `packages` so py2app copies it unzipped —
the launcher reads web/builder.html off disk via __file__, which only works when
the package is a real directory in the bundle.

`iterm2` (the macOS terminal backend) is imported lazily inside functions, so
py2app's static import graph misses it — naming it under `packages` forces it in,
and py2app then scans it and pulls its deps (websockets, google.protobuf).
"""
from setuptools import setup

setup(
    app=["app_main.py"],
    name="Terminal Launcher",
    options={"py2app": {
        "argv_emulation": False,
        "iconfile": "packaging/icon.icns",
        "packages": ["terminal_launcher", "webview", "iterm2"],
        "plist": {
            "CFBundleName": "Terminal Launcher",
            "CFBundleDisplayName": "Terminal Launcher",
            "CFBundleIdentifier": "com.dberardi.terminal-launcher",
            "CFBundleShortVersionString": "1.4.0",
            "LSUIElement": False,
            "NSHighResolutionCapable": True,
            # Required so macOS shows the Automation consent prompt (instead of
            # silently denying Apple Events). iTerm2's Python API obtains its auth
            # cookie via AppleScript, which is an Apple Event to iTerm2.
            "NSAppleEventsUsageDescription":
                "Terminal Launcher controls iTerm2 to open your tiled Claude "
                "Code layouts.",
        },
    }},
    setup_requires=["py2app"],
)
