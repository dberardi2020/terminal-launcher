# 0009 — Restore pane identity after `/clear`

**Status:** Accepted · **Date:** 2026-07-21

## Context

A launched pane carries an identity — the Claude session name, the window/tab title, and
the prompt-bar `/color` (see [ADR 0002](0002-identity-injection.md)). Claude Code's
`/clear`, and reconnecting to a session, resets the *in-session* parts: the `/color` and the
session name are gone, even though the pane is still "the API pane." There's no event to
hook, so re-applying identity has to be an explicit, on-demand action.

The tool is cross-platform (iTerm2 on macOS, Windows Terminal on Windows), so restore must
not become a macOS-only bolt-on. (An earlier attempt was exactly that — a standalone script
that hardcoded the iTerm2 API.)

## Decision

**A `restore` capability that splits the same way the launcher does: cross-platform
detection, backend-delegated injection.**

- **Detection** (`restore.py`, platform-agnostic): match the current working directory
  against each pane's `target` (longest match wins), with a per-session sentinel — keyed by
  `ITERM_SESSION_ID` / `WT_SESSION` — that remembers the identity after you `cd` away.
- **Injection** through the existing backend seam: `backend.restore_identity(color, name)` →
  the active backend's `restore_current`, reusing the launch-time delivery paths but aimed at
  the *current* session.
- Exposed as `terminal-launcher restore` (also `python -m terminal_launcher restore`), and
  surfaced to Claude Code as a `/restore` slash command under
  [`integrations/claude-code/`](../../integrations/claude-code/README.md) — a template + an
  installer that bakes this checkout's paths in.

## Rationale

- **Cross-platform by construction.** Only injection is platform-specific, and the tool
  already has both implementations; restore reuses them rather than reimplementing one.
- **Detection is the reusable, testable core.** It's pure (cwd + config), so it's unit-tested
  once (`tests/test_restore.py`) and behaves identically on every platform.
- **A Claude Code integration, not a general CLI use.** Restore only makes sense inside a
  launched pane, so the primary UX is the `/restore` slash command; the CLI verb is the
  mechanism it calls.

## Consequences

- Restore targets the *current* session (`ITERM_SESSION_ID`, or the foreground `wt` window) —
  a need the backends didn't have before. `restore_current` becomes a fourth backend-contract
  function; the Windows launch path's paste logic is extracted into a shared `_paste_command`.
- The **macOS** path is verified; the **Windows Terminal** injector (foreground-window +
  clipboard-paste) is implemented but **pending a real-session check**, like the rest of the
  Windows backend — tracked in the backlog.
- Supersedes the earlier standalone `integrations/claude-code/restore.py`; the logic now lives
  in the package and the integration only installs the slash command.
