# Claude Code integration — `/restore`

Terminal Launcher tags every launched pane with a **name** and **colour** so you can
tell your Claude Code sessions apart at a glance (the session name, the pane title, and
the prompt-bar `/color`). Claude Code's **`/clear`** — and reconnecting to a session —
resets that in-session identity: the colour and rename are gone even though the pane is
still "the API pane."

`/restore` puts it back. Run it right after `/clear` and it re-detects which pane you're
in (from the working directory, against Terminal Launcher's `panes` registry) and
re-issues the `/color` and `/rename` for you. It's the natural companion to launching —
it reads the same config Terminal Launcher launches from.

## Install

```sh
./integrations/claude-code/install.sh          # installs as /restore
./integrations/claude-code/install.sh tl-restore   # or pick your own command name
./integrations/claude-code/install.sh --uninstall  # remove it
```

The installer writes `~/.claude/commands/<name>.md` with this checkout's venv-python and
script paths baked in. **Re-run it if you move the checkout.** It needs the venv built
with the `iterm2` library (see the repo README) — that's the interpreter `/restore` uses
to talk to iTerm2.

## Use

Inside any pane Terminal Launcher launched, after a `/clear`:

```
/restore
```

You can pass a follow-up task — `/restore <task>` — and it continues with that once the
identity is re-applied (restore is fire-and-forget and doesn't block).

## How it works (and why it's macOS/iTerm2 only)

`restore.py` finds your pane's identity by matching the current directory to a pane's
`target` in `~/.config/terminal-launcher/workspaces.json` (remembering the match in a
per-session sentinel so it still works after you `cd` away), then injects the two
commands into the **current** iTerm2 session over iTerm2's Python API — addressed to the
session directly, so it needs no window focus and no Accessibility permission. That API
is iTerm2-specific, so `/restore` is macOS-only today (the same platform seam as the
launcher's iTerm2 backend).
