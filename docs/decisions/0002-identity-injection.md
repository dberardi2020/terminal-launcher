# 0002 — Pane identity injection

**Status:** Accepted · **Date:** 2026-07-10

## Context

A pane's whole point is a persistent **identity** — `name · color · target ·
model`. On launch, that identity must show up *in the running session*, not just
in the config, so a glance at the screen tells you which pane is which. The
predecessor did this on Windows by naming the Claude session, titling
the window, and typing `/color <name>` into the prompt.

Replicating "type `/color` into a specific pane" is exactly where naive
approaches break: a global keystroke send (AppleScript `keystroke`, Terminal.app)
goes to whatever pane has focus and needs macOS **Accessibility** permission — a
fragile, permission-gated gamble when several panes launch at once.

## Decision

Apply identity three ways, all through `wezterm cli`:

1. **Session name** — `claude -n <name>` when spawning the pane.
2. **Tab title** — `wezterm cli set-tab-title --pane-id <id> <name>`.
3. **Prompt color** *(optional)* — inject `/color <name>` into the pane via
   `wezterm cli send-text --pane-id <id>`, gated by `--inject-color` /
   `settings.injectColor`.

Injection is **addressed to a specific pane-id**, so it needs no focus and no
Accessibility permission — the reason WezTerm was chosen as the terminal layer
([ADR 0001](0001-terminal-layer-and-core.md)).

## The submit bug (and the fix)

Injecting `/color <name>` in one call **types the text but does not submit it** in
Claude's TUI — verified empirically: the prompt sat at `❯ /color cyan`,
unexecuted. Appending `\r` to the same `send-text` payload did **not** help.

**The fix is two separate `send-text` calls:** first the text, then a *lone
carriage return*. Two calls reliably submit where one does not. This is baked into
`wezterm.py:_inject_color`:

```python
send(f"/color {color}")   # types the command
time.sleep(0.4)
send("\r")                # a SEPARATE call submits it
```

## Timing

Injection only works once the Claude TUI has started and is accepting input, so
it runs after a delay (`settings.colorDelay`, default 1.5s) measured from launch.
Too short and the keystrokes land before the prompt exists. If injection ever
proves flaky under load, the fallback is to poll the pane (`wezterm cli get-text`)
for the prompt before sending, rather than sleeping a fixed interval.

## Consequences

- Color injection is functional and permission-free, not best-effort.
- It is **optional** — off by default in a bare config; `set-tab-title` and the
  session name give identity even without it.
- The two-step submit is load-bearing: collapsing it back into one `send-text`
  silently reintroduces the "typed but not submitted" bug. Keep the calls
  separate.
