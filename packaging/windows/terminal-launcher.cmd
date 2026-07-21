@echo off
rem Launch the Terminal Launcher visual composer with no console window.
rem
rem The zero-bundle Windows path: no PyInstaller build needed. Requires Python on PATH and
rem pywebview installed (pip install pywebview). Pin this to Start or make a desktop
rem shortcut for a double-clickable GUI.
rem
rem cd to the repo root (two levels up from this file) so `-m terminal_launcher` resolves.
cd /d "%~dp0..\.."
start "" pythonw -m terminal_launcher gui
