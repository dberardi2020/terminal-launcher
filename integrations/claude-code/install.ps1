<#
  Install (or remove) the Terminal Launcher `/restore` slash command for Claude Code.

      powershell -ExecutionPolicy Bypass -File integrations\claude-code\install.ps1
      powershell -ExecutionPolicy Bypass -File integrations\claude-code\install.ps1 -Name tl-restore
      powershell -ExecutionPolicy Bypass -File integrations\claude-code\install.ps1 -Uninstall

  Writes %USERPROFILE%\.claude\commands\<name>.md from restore.md.template with this
  checkout's python + entry-point paths baked in, so /restore works from any launched pane.
  Re-run after moving the checkout.

  This is the Windows twin of install.sh — same command name, same template, same generated
  file. Only the invocation line differs (see $run below).
#>
param([string]$Name = 'restore', [switch]$Uninstall)

$ErrorActionPreference = 'Stop'

$here   = $PSScriptRoot
$repo   = (Resolve-Path (Join-Path $here '..\..')).Path
$cmdDir = Join-Path $env:USERPROFILE '.claude\commands'
$dest   = Join-Path $cmdDir "$Name.md"

if ($Uninstall) {
    if (Test-Path $dest) { Remove-Item $dest -Force; Write-Output "Removed /$Name ($dest)" }
    else                 { Write-Output "nothing to remove at: $dest" }
    return
}

$python = Join-Path $repo '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw "no venv python at '$python'. Create the venv first (it needs the project deps) - see the README."
}

$entry = Join-Path $repo 'bin\terminal-launcher'
if (-not (Test-Path $entry)) {
    throw "entry point not found at '$entry'."
}

# Forward slashes: the generated line is run by Claude Code's shell, which is bash-flavoured
# on Windows too, and bash treats backslashes as escapes. No `env -u` prefix here - the
# PYTHONHOME/PYTHONPATH scrubbing install.sh does guards against a macOS .app quirk that has
# no Windows equivalent. The entry script puts the repo on sys.path itself, so no PYTHONPATH.
$py  = $python -replace '\\', '/'
$ent = $entry  -replace '\\', '/'
$run = "`"$py`" `"$ent`" restore"

New-Item -ItemType Directory -Force -Path $cmdDir | Out-Null
(Get-Content (Join-Path $here 'restore.md.template') -Raw).Replace('{{RUN}}', $run) |
    Set-Content -Path $dest -Encoding UTF8 -NoNewline

Write-Output "Installed /$Name -> $dest"
Write-Output "  runs: $run"
Write-Output "Use it inside any launched Claude Code pane: run /$Name right after /clear."
