# Tickets

The backlog. Board-first: a lightweight tracker until a real one is warranted. IDs are `TLA-NNNN`, uppercase, never reused.

**What is *not* here:** the steps to *take the repo public* — secrets scan, private-content sweep, the flip. Those are a **pre-flight checklist run once when the project is ready**, kept as a separate release runbook, not backlog. This board tracks *building the product*.

Rows are pointers; anything needing more than a sentence has a block in **Details**, below the board. A linked title means the ticket has its own folder — artifacts and a longer breakdown live there.

## In progress

*(none)*

## On deck

*(none — nothing committed yet.)*

## Blocked

| ID | Pri | Type | Title |
|---|---|---|---|
| [TLA-0022](#tla-0022) | P3 | Chore | Drop `bin/terminal-launcher` — blocked on the `/restore` installers |

## Backlog

| ID | Pri | Type | Title |
|---|---|---|---|
| [TLA-0001](#tla-0001) | P2 | Chore | Integration tests: launch each layout, assert window/pane structure via iTerm2 API read-back |
| [TLA-0007](TLA-0007/) | P2 | Bug | Panes list overflows on long paths, pushing edit/delete icons past the panel edge |
| [TLA-0010](#tla-0010) | P2 | Chore | Streamline pushing updates to the installed Dock app |
| [TLA-0012](#tla-0012) | P2 | Feature | Design the install/setup and maintenance/update flows |
| [TLA-0013](#tla-0013) | P2 | Feature | Visual loading animation during launch |
| [TLA-0014](#tla-0014) | P2 | Feature | Multi-monitor placement |
| [TLA-0016](TLA-0016/TLA-0016.md) | P2 | Feature | Non-interactive config CLI |
| [TLA-0023](TLA-0023/TLA-0023.md) | P2 | Chore | Audit error handling, reporting & logging |
| [TLA-0025](#tla-0025) | P2 | Bug | First launch fires 10+ permission prompts |
| [TLA-0027](#tla-0027) | P2 | Chore | Re-land the `src/` layout migration once packaged builds are verified |
| [TLA-0003](#tla-0003) | P3 | Chore | Ad-hoc sign the py2app bundle to stop TCC/Automation re-prompting |
| [TLA-0004](#tla-0004) | P3 | Feature | Themes — appearance is hardcoded One Dark / Menlo 13 |
| [TLA-0005](#tla-0005) | P3 | Bug | Cold-start window restoration reopens prior tool windows on relaunch |
| [TLA-0015](#tla-0015) | P3 | Feature | Revisit Windows Terminal tab tinting |
| [TLA-0017](TLA-0017/TLA-0017.md) | P3 | Feature | GUI automation / demo hooks |
| [TLA-0018](TLA-0018/TLA-0018.md) | P3 | Feature | Hosted browser demo (GitHub Pages) |
| [TLA-0020](TLA-0020/TLA-0020.md) | P3 | Feature | A family of management commands |
| [TLA-0024](#tla-0024) | P3 | Chore | Move the ticket board to GitHub Projects |
| [TLA-0026](#tla-0026) | P3 | Bug | `restore` emits a scary ERROR on the happy path as a background job |
| [TLA-0028](#tla-0028) | P3 | Feature | No way to tell what Default actually resolves to for a pane |

## Done

*Entries describe what each item delivered at the time it closed, so figures in them
(test counts, layout lists) are historical, not the current state — the living numbers
are in the docs.*

| ID | Title | Closed |
|---|---|---|
| TLA-0021 | **Dock app leaked `PYTHONHOME`/`PYTHONPATH` into launched panes** — the `.app` set both to its own `Contents/Resources`, and because a cold start launches iTerm2 itself, every pane inherited them; any `python` in a pane resolved the bundle's stdlib (a `pipx`-installed `terminal-launcher` silently ran the stale bundled copy). Fixed three ways: `backend.scrub_bundled_python_env()` at both entry points (root cause, cold start); an `env -u PYTHONHOME -u PYTHONPATH` prefix on each pane command (covers an already-polluted iTerm2); and `packaging/install-macos.sh` now unsets both — the build itself failed (`No module named 'jaraco.functools'`) when run from a polluted pane, resolving setuptools out of the *bundle's* stdlib. 5 tests. **Verified end-to-end:** with the rebuilt `.app` installed, a pane launched from a polluted shell — with a probe value injected into `PYTHONPATH` — came up with **neither variable and no probe**, while a pane launched before the fix still shows both. | 2026-07-21 |
| TLA-0011 | Dropped WezTerm entirely; unified on the native iTerm2 separate-window backend (non-macOS raises a clear "Windows Terminal planned" error). Branch `unify-mac-and-strip-wezterm` — verified: 21 tests, quad → 4 tiled windows, `/color`, GUI. | 2026-07-21 |
| TLA-0008 | GUI backend gate-key renamed `wezterm` → `terminal` (badge "No terminal backend"), so the Launch gate no longer misnames iTerm2. Fixed alongside the WezTerm strip. | 2026-07-21 |
| TLA-0002 | Obsolete — `wezterm.py` removed with the WezTerm strip (TLA-0011), so its duplicate `SPLIT_PLAN` is gone; `layouts.py` is now the sole source. | 2026-07-21 |
| TLA-0019 | Verified `/restore` on Windows end-to-end: detection (3/3 panes, longest-match, `WT_SESSION` sentinel, UNKNOWN), live `/color` + `/rename` both landing and submitting in the correct `wt` window, no launch-time regression from the `_paste_command` extraction, clipboard preserved, and `install.ps1` generating a working command line. Fixed three defects found in review — ambiguous multi-window fallback, clipboard leak on the bail-out path, and injection failures reported as success — plus dropped `install.ps1`'s macOS-inherited venv requirement (Windows needs no third-party deps). See [ADR 0009](../decisions/0009-restore-pane-identity.md). | 2026-07-21 |
| TLA-0006 | Sync docs to the iTerm2 pivot: new [ADR 0007](../decisions/0007-iterm2-backend-and-real-gap-layouts.md), README/concept updates, version bump (commit `79a0aff`). | 2026-07-17 |
| TLA-0009 | `db-restore` — global skill restoring pane identity (`/color` + `/rename`) from the TL `panes` config, matched by cwd, via the iTerm2 API. Script `~/.claude/scripts/db-restore.py` + command `db-restore.md`. | 2026-07-17 |

## Details

### TLA-0001 — Integration tests via iTerm2 API read-back {#tla-0001}
**P2 · Chore · tests**

Launch each layout, then assert the resulting window/pane structure and frames by reading back through the iTerm2 API, rather than trusting the launch call returned cleanly.

### TLA-0003 — Ad-hoc sign the py2app bundle {#tla-0003}
**P3 · Chore · packaging**

To stop TCC/Automation re-prompting after each rebuild. Inflates how often **TLA-0025** is hit, since every unsigned rebuild re-triggers the consent wall.

### TLA-0004 — Themes {#tla-0004}
**P3 · Feature · ux**

Appearance is hardcoded One Dark / Menlo 13; the dynamic profile is fully configurable, so the hardcoding is the only thing standing between here and user-selectable themes.

### TLA-0005 — Cold-start window restoration reopens prior tool windows {#tla-0005}
**P3 · Bug · backend**

On relaunch. Benign, and left alone deliberately to avoid closing real work.

### TLA-0010 — Streamline pushing updates to the installed Dock app {#tla-0010}
**P2 · Chore · packaging**

So code changes don't need a full py2app rebuild + reinstall each time — evaluate py2app **alias mode** (`python setup.py py2app -A`), a symlinked package, or launching the GUI from source. The narrow dev-loop fix that **TLA-0012** is the umbrella over.

### TLA-0012 — Design the install/setup and maintenance/update flows {#tla-0012}
**P2 · Feature · packaging**

For going live as an ongoing project — first-run setup (deps, iTerm2, Automation grant, config seed) + a repeatable release/update path (version bump, rebuild, swap). The umbrella over the narrower dev-loop fix in **TLA-0010**, and the right place to explain and sequence the grants **TLA-0025** cuts down.

### TLA-0013 — Visual loading animation during launch {#tla-0013}
**P2 · Feature · ux**

So the composer doesn't look frozen while the backend spawns windows and injects `/color` — the launch runs on a background thread with color-injection sleeps, leaving the window idle for a few seconds.

### TLA-0014 — Multi-monitor placement {#tla-0014}
**P2 · Feature · backend**

Slot rects derive from the *primary* monitor's work area only (`SPI_GETWORKAREA` on Windows, main display on macOS), so a workspace always lands on the primary display. Add per-monitor targeting — relevant now that the PC is a multi-display setup.

### TLA-0015 — Revisit Windows Terminal tab tinting {#tla-0015}
**P3 · Feature · ux**

`--tabColor <pane hex>` was implemented then dropped ([ADR 0008](../decisions/0008-one-window-per-pane-and-windows-terminal-backend.md)) — the composer's swatch hexes don't read well against wt's own theming. Needs a palette tuned for `wt`, not a reuse of the pane colours.

### TLA-0022 — Drop `bin/terminal-launcher` {#tla-0022}
**P3 · Chore · packaging**

Now that `pyproject.toml` ships a `console_scripts` entry point (and `python -m terminal_launcher` covers the checkout case), the `bin/` shim is redundant.

**Blocker:** the `/restore` installers currently invoke it. Move them to the installed `terminal-launcher` (with a `python -m` fallback for checkout-only users), then delete `bin/` and its doc references.

### TLA-0024 — Move the ticket board to GitHub Projects {#tla-0024}
**P3 · Chore · tooling**

An in-repo MD+HTML board fit a private solo repo; a public one gets Issues/Projects for free — cross-links to commits and PRs, and no lockstep render to maintain. Needs a call on what migrates (Backlog rows, the Done history, `TLA-NNNN/` folders and their screenshots) and whether the `TLA-NNNN` IDs survive as labels.

The board format itself is documented as interim in `.meta/ticket-board-standard.md`, with GitHub Projects named as the destination; **CSK-0010** is the sibling ticket.

### TLA-0025 — First launch fires 10+ permission prompts {#tla-0025}
**P2 · Bug · packaging**

Opening the installed `.app` throws a wall of macOS consent dialogs at the user — enough that it reads as broken/untrustworthy on first run. Needs an audit of *which* grants are actually being requested and by whom (Automation → iTerm2 for the Python API's AppleScript auth cookie, `open -a iTerm`, plus whatever each pane's `cwd` trips: Documents/Desktop/Downloads/iCloud), then a cut down to the minimum set, ideally requested lazily at the point of use rather than all at open.

Related: **TLA-0003** (unsigned bundle re-prompts after every rebuild, which inflates how often this is hit) and **TLA-0012** (first-run setup flow — the right place to explain/sequence the grants that genuinely are required).

### TLA-0026 — `restore` emits a scary ERROR on the happy path as a background job {#tla-0026}
**P3 · Bug · ux**

With no `ITERM_SESSION_ID` in a background job's env, `restore_current` (`iterm2_backend.py:276-279`) can't resolve the pane and raises `could not resolve this iTerm2 session (no ITERM_SESSION_ID)`, which surfaces through `ERROR`, even though `detect` succeeded and `/color` + `/rename` still land. So a successful restore repeatedly reads as a failure ("detected this pane but the API returned no session ID"). Downgrade the no-`ITERM_SESSION_ID`/background case to a quiet no-op (or benign note) rather than an ERROR. Same "success-looked-like-failure" family as the reporting audit in **TLA-0023**.

### TLA-0027 — Re-land the `src/` layout migration {#tla-0027}
**P2 · Chore · packaging**

Once the packaged builds are verified. The move of `terminal_launcher/` → `src/terminal_launcher/` (house standard's Python `src/`-layout rule) lives on the **`src-layout`** branch; it was reverted from `main` (revert `d42ac4e`) because the py2app `.app` and PyInstaller `.exe` bundles couldn't be build-tested locally — only `pip install -e .`, the 32-test suite, `python -m terminal_launcher`, the console script, `bin/terminal-launcher`, and the `app_main` import were verified.

**To finish:** build the macOS `.app` (`python setup_py2app.py py2app`) and confirm the GUI launches and reads `builder.html` off disk; build the Windows `.exe` from the spec and confirm the same; then rebase `src-layout` onto `main` and merge. The spec changes are already on the branch — `pyproject` `package-dir = { "" = "src" }`, `bin` sys.path → `src/`, a `src/` sys.path insert in `setup_py2app.py`, and the PyInstaller data source `src/terminal_launcher/web` with `pathex=['src']`.

### TLA-0028 — No way to tell what Default actually resolves to {#tla-0028}
**P3 · Feature · ux**

For a given or selected pane. The UI shows "Default" but never surfaces the concrete value it resolves to, so you can't see what a pane will actually use without changing it.

## Conventions

The house standard for this board's shape — lanes, schema, detail tiers, archiving — is
`.meta/ticket-board-standard.md` in the author's workspace. The essentials, so this file
stands alone:

- **Source of truth is this file.** Edit the tables directly, then regenerate the render:
  `python docs/render.py docs/tickets/tickets.md`. Commit both files together.
- **IDs** are `TLA-NNNN`, one sequence, assigned in creation order (not priority), never
  renumbered and never reused.
- **Lanes**, in order: In progress · On deck · Blocked · Backlog · Done. An empty lane keeps
  its heading and reads `*(none)*`.
- **Priority:** P1 (soon) → P2 (real, not next) → P3 (someday). **Type:** Bug · Feature ·
  Chore (housekeeping — tests, refactors, packaging, docs) · Idea (not yet scoped).
- **Rows are sorted by priority**, ties by ID — except **On deck**, which is in intended
  sequence, and **Done**, which is reverse-chronological.
- **Keep rows short — length is the signal.** A row is a pointer, one sentence. Anything
  longer gets a `### TLA-NNNN` block under **Details** (ID-ordered), or — when it has
  **artifacts** — its own `TLA-NNNN/` folder linked from the row's title. Evidence goes
  under `TLA-NNNN/Screenshots/`; fresh captures stage in the gitignored `screenshots/`
  inbox. `Done` rows are exempt — there the row *is* the record.
- **Archiving:** when **Done** gets long, move rows to `archive/tickets.md`; a closed ticket
  that had a folder moves to `archive/TLA-NNNN/`.
- **A literal `|` in a cell spawns a phantom column** — the renderer splits rows naively.
  Use `/` inside cells.
