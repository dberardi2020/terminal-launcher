# Terminal Launcher — Documentation

The map of this folder. Four kinds of doc, by audience and purpose:

| Folder / file | For whom | Purpose |
|---|---|---|
| **[Product/](product/README.md)** | *any* stakeholder | What Terminal Launcher is, the model, and how to use it — no code assumed. |
| **[Technical/](technical/README.md)** | developers | How the code is built — architecture, modules, backends, data model, packaging. |
| **[decisions/](decisions/)** | anyone going deep | Architecture Decision Records — *why* each choice was made (start with [0001](decisions/0001-terminal-layer-and-core.md) and [0007](decisions/0007-iterm2-backend-and-real-gap-layouts.md)). |
| **[tickets/](tickets/tickets.md)** | maintainers | The lightweight backlog (board-first). |

## Where to start

- **New to the product?** → [Product/Overview](product/overview.md), then
  [Product/Concepts](product/concepts.md).
- **Going to use it?** → [Product/User Guide](product/user-guide.md).
- **Going to work on the code?** → [Technical/Architecture](technical/architecture.md),
  then [Technical/Module Reference](technical/module-reference.md).

## How these relate

`decisions/` is the **primary source** — the decision history. `Product/` and `Technical/`
are the **reader-facing suites** that synthesize it for their audiences and link back rather
than duplicate. When they disagree, the ADRs win (they carry the current decision state).

The concept model lives in **[Product/Concepts](product/concepts.md)** and nowhere else —
there is deliberately no second top-level concept doc restating it.

## Doc convention

Filenames are lowercase kebab-case (`README.md` is the one exception), folders are lowercase,
and ticket IDs stay uppercase. Every folder holding more than one prose doc carries a
`README.md` index.

Every prose doc here is a **Markdown + HTML pair** in lock-step: the `.md` is the source
of truth, the `.html` is a styled render of the same content. After editing a `.md`,
regenerate its `.html`:

```sh
python docs/render.py docs/<path>/<file>.md      # one file
python docs/render.py docs/technical/*.md         # a whole folder
```

`render.py` is stdlib-only; there's no other docs build step.
