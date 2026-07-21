"""Terminal Launcher — compose and launch tiled Claude Code sessions.

A shared core (config + composition model) behind a terminal-backend seam:
iTerm2 on macOS and Windows Terminal on Windows — both placing one real OS window
per pane by geometry, with real desktop gaps for empty slots. Other platforms
have no native backend.
"""

__version__ = "1.4.0"
