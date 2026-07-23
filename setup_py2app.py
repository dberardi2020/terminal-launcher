"""macOS .app packaging for Terminal Launcher's visual composer (py2app).

    python setup_py2app.py py2app   # builds dist/Terminal Launcher.app

`terminal_launcher` is listed under `packages` so py2app copies it unzipped —
the launcher reads web/builder.html off disk via __file__, which only works when
the package is a real directory in the bundle.

`iterm2` (the macOS terminal backend) is imported lazily inside functions, so
py2app's static import graph misses it — naming it under `packages` forces it in,
and py2app then scans it and pulls its deps (websockets, google.protobuf).

Kept separate from `pyproject.toml` (the pip/pipx packaging source of truth) so a
`pip install` never drags in a py2app build — see `_Py2appDistribution` for the one
place the two still collide.
"""
from setuptools import setup
from setuptools.dist import Distribution


class _Py2appDistribution(Distribution):
    """Hide `install_requires` from py2app.

    py2app hard-errors with "install_requires is no longer supported" when the
    distribution has any requirements, and setuptools now populates them from
    `pyproject.toml`'s `[project].dependencies` — which it reads because that file
    sits next to this one. The bundle doesn't need them anyway: it vendors its deps
    directly via the `packages` option below. Clearing in `run_commands` (rather
    than passing `install_requires=[]`) guarantees it happens *after* setuptools has
    applied the pyproject metadata, so it can't be overwritten."""

    def run_commands(self):
        self.install_requires = []
        super().run_commands()


setup(
    distclass=_Py2appDistribution,
    app=["app_main.py"],
    name="Terminal Launcher",
    version="1.4.0",
    description="Compose and launch tiled Claude Code sessions with one command.",
    author="Dimitri Berardi",
    license="MIT",
    url="https://github.com/dberardi2020/terminal-launcher",
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
