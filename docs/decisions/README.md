# Decision records

Architecture decisions for Terminal Launcher — the *why* behind the build.
Each records context, the options weighed, the decision, and its consequences.

| # | Decision | Status |
|---|---|---|
| [0001](0001-terminal-layer-and-core.md) | Terminal layer: **WezTerm** + a thin **Python core** | Accepted · amended by [0007](0007-iterm2-backend-and-real-gap-layouts.md), [0008](0008-one-window-per-pane-and-windows-terminal-backend.md) |
| [0002](0002-identity-injection.md) | Pane **identity injection** (name · title · `/color`, two-step submit) | Accepted |
| [0003](0003-visual-composer-pywebview.md) | **Visual composer**: a fleeting native window (pywebview) | Accepted |
| [0004](0004-heterogeneous-panes-and-window-placement.md) | **Heterogeneous panes** (Chrome/Finder/…) via OS-window placement | Proposed |
| [0005](0005-combo-flip-and-partial-compaction.md) | **Combo layout**, horizontal **flip**, and partial-layout **compaction** | Accepted · Decision 3 (compaction) superseded by [0008](0008-one-window-per-pane-and-windows-terminal-backend.md) (had been amended by [0007](0007-iterm2-backend-and-real-gap-layouts.md)) |
| [0006](0006-workspace-reordering-affordance.md) | **Workspace reordering**: inline arrows + Jump-to-front/end in the ⋯ menu | Accepted |
| [0007](0007-iterm2-backend-and-real-gap-layouts.md) | **macOS terminal layer → iTerm2** backend + **real-gap** partial layouts | Accepted · full-layout behavior superseded by [0008](0008-one-window-per-pane-and-windows-terminal-backend.md) |
| [0008](0008-one-window-per-pane-and-windows-terminal-backend.md) | **One window per pane** (all layouts) + a **Windows Terminal** backend; WezTerm removed | Accepted |

Numbered, append-only. A superseded decision stays and is marked
`Superseded by NNNN` rather than edited away.
