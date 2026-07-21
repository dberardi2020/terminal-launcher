<#
  Install (or remove) a Start Menu shortcut for the Terminal Launcher visual composer.

      powershell -ExecutionPolicy Bypass -File packaging\windows\install-shortcut.ps1
      powershell -ExecutionPolicy Bypass -File packaging\windows\install-shortcut.ps1 -Uninstall

  The shortcut runs the GUI with `pythonw` (no console window) straight from this
  checkout — no PyInstaller build required. Needs Python + pywebview installed.
  For a standalone .exe instead, see terminal-launcher.spec.
#>
param([switch]$Uninstall)

$ErrorActionPreference = 'Stop'

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$lnk  = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Terminal Launcher.lnk'

$iconDir = Join-Path $env:LOCALAPPDATA 'Terminal Launcher'
$icon    = Join-Path $iconDir 'app.ico'

if ($Uninstall) {
    if (Test-Path $lnk) { Remove-Item $lnk -Force; Write-Output "removed: $lnk" }
    else                { Write-Output "nothing to remove at: $lnk" }
    if (Test-Path $iconDir) { Remove-Item $iconDir -Recurse -Force; Write-Output "removed: $iconDir" }
    return
}

# Resolve pythonw.exe next to whatever interpreter the `py` launcher selects.
$pythonw = & py -c "import sys, os; print(os.path.join(os.path.dirname(sys.executable), 'pythonw.exe'))"
if (-not (Test-Path $pythonw)) {
    throw "pythonw.exe not found (looked at '$pythonw'). Is Python installed?"
}

# Copy the icon out of the checkout into LocalAppData and point the shortcut there.
# Two reasons: the shortcut keeps working if the checkout ever moves, and Windows'
# shell icon cache will happily serve a stale icon for a path it has already seen —
# even after the file changes — so a fresh path is the reliable way to bust it.
$src = Join-Path $repo 'packaging\windows\app.ico'
if (Test-Path $src) {
    New-Item -ItemType Directory -Force -Path $iconDir | Out-Null
    Copy-Item $src $icon -Force
}

$sc = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
$sc.TargetPath       = $pythonw
$sc.Arguments        = '-m terminal_launcher gui'
$sc.WorkingDirectory = $repo          # so `-m terminal_launcher` resolves from the checkout
$sc.Description      = 'Compose and launch tiled Claude Code sessions'
if (Test-Path $icon) { $sc.IconLocation = $icon }
$sc.Save()

Write-Output "installed: $lnk"
Write-Output "  target : $pythonw -m terminal_launcher gui"
Write-Output "  workdir: $repo"
Write-Output "  icon   : $(if (Test-Path $icon) { $icon } else { '(none - app.ico missing)' })"
