#!/usr/bin/env bash
# Install the Terminal Launcher `/restore` slash command into Claude Code.
#
# It writes ~/.claude/commands/<name>.md (default: restore) with this checkout's
# venv-python path and script path baked in, so `/restore` works from any launched
# pane. Re-run after moving the checkout. Needs the venv built (with the `iterm2`
# lib) — see the repo README / packaging/README.md.
#
# Usage:
#   ./integrations/claude-code/install.sh [name]     # install as /<name> (default: restore)
#   ./integrations/claude-code/install.sh --uninstall [name]
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
CMD_DIR="$HOME/.claude/commands"

NAME="restore"
UNINSTALL=0
for arg in "$@"; do
  case "$arg" in
    --uninstall) UNINSTALL=1 ;;
    -*)          echo "unknown option: $arg" >&2; exit 2 ;;
    *)           NAME="$arg" ;;
  esac
done

DEST="$CMD_DIR/$NAME.md"

if [[ "$UNINSTALL" == 1 ]]; then
  rm -f "$DEST" && echo "Removed /$NAME ($DEST)"
  exit 0
fi

PYTHON="$REPO/.venv/bin/python"
SCRIPT="$HERE/restore.py"

if [[ ! -x "$PYTHON" ]]; then
  echo "error: no venv python at '$PYTHON'." >&2
  echo "       Build the venv first (it needs the 'iterm2' lib) — see the README." >&2
  exit 1
fi

mkdir -p "$CMD_DIR"
sed -e "s|{{PYTHON}}|$PYTHON|g" -e "s|{{SCRIPT}}|$SCRIPT|g" \
  "$HERE/restore.md.template" > "$DEST"

echo "Installed /$NAME -> $DEST"
echo "  python: $PYTHON"
echo "  script: $SCRIPT"
echo "Use it inside any launched Claude Code pane: run /$NAME right after /clear."
