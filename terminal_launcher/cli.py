"""Command-line interface for Terminal Launcher.

Verbs:
  list                     list saved workspaces
  panes                    list configured panes
  preview <name>           text preview of a workspace's layout
  launch <name>            launch a workspace (add --dry-run to just print)
  new                      interactively compose a NEW workspace and save it
  edit <name>              interactively edit an existing workspace
  delete <name>            remove a workspace
  pane-new                 interactively add a new pane (terminal identity)
  init                     create a starter config from the bundled example

The `new` / `edit` / `pane-new` verbs are the fix for the old GUI's limitation:
compositions can be created and changed from here and are written straight back
to the config file.
"""

from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path

from . import backend
from . import config as cfg
from . import diag
from .config import LAYOUT_CAPACITY
from .model import (
    CompositionError,
    find_workspace,
    resolve_workspace,
)

# ---- tiny ANSI helpers (no dependency) -------------------------------------

def _supports_color() -> bool:
    return sys.stdout.isatty()

def c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _supports_color() else text

def bold(t): return c(t, "1")
def dim(t): return c(t, "2")
def cyan(t): return c(t, "36")
def green(t): return c(t, "32")
def yellow(t): return c(t, "33")
def red(t): return c(t, "31")

def swatch(color_name: str) -> str:
    hexmap = {
        "blue": "39;5;69", "orange": "38;5;179", "red": "38;5;203",
        "purple": "38;5;141", "green": "38;5;107", "cyan": "38;5;73",
        "pink": "38;5;175", "gray": "38;5;245",
    }
    code = hexmap.get(color_name, "38;5;245")
    return c("●", code) if _supports_color() else "*"


# ---- config loading with friendly errors ------------------------------------

def _load_or_die(path: Path) -> dict:
    if not path.exists():
        print(red(f"No config at {path}"))
        print(f"Run {bold('terminal-launcher init')} to create one, "
              f"or {bold('terminal-launcher new')} to compose your first workspace.")
        sys.exit(1)
    return cfg.load(path)


def _load_or_seed(path: Path) -> dict:
    if not path.exists():
        print(dim(f"Creating config at {path}"))
        return cfg.seed_from_example(path)
    return cfg.load(path)


# ---- rendering --------------------------------------------------------------

LAYOUT_GLYPH = {
    "single": "■",
    "split": "■■",
    "combo": "█|▪▪",
    "quad": "■■/■■",
}

def _pane_summary(config: dict, ws: dict) -> str:
    names = []
    for i in range(LAYOUT_CAPACITY.get(ws.get("layout", "single"), 1)):
        slots = ws.get("slots", [])
        slot = slots[i] if i < len(slots) else None
        pid = slot.get("pane") if isinstance(slot, dict) else None
        if not pid:
            names.append(dim("(empty)"))
        else:
            pane = config["panes"].get(pid, {})
            names.append(swatch(pane.get("color", "gray")) + " " + pane.get("name", pid))
    return "  ".join(names)


def cmd_list(config: dict, args) -> int:
    wss = config.get("workspaces", [])
    if not wss:
        print(dim("No workspaces yet. Run `terminal-launcher new`."))
        return 0
    print(bold("Workspaces"))
    for ws in wss:
        layout = ws.get("layout", "single")
        head = f"  {cyan(ws['name']):<24} {dim(LAYOUT_GLYPH.get(layout, layout))}"
        print(f"{head}  {_pane_summary(config, ws)}")
    return 0


def cmd_panes(config: dict, args) -> int:
    panes = config.get("panes", {})
    if not panes:
        print(dim("No panes yet. Run `terminal-launcher pane-new`."))
        return 0
    print(bold("Panes"))
    for pid, p in panes.items():
        print(f"  {swatch(p.get('color','gray'))} {cyan(p.get('name', pid)):<20} "
              f"{dim(p.get('target',''))}  {dim(p.get('model',''))}")
    return 0


def cmd_preview(config: dict, args) -> int:
    ws = find_workspace(config, args.name)
    if not ws:
        print(red(f"No workspace named '{args.name}'"))
        return 1
    try:
        slots = resolve_workspace(config, ws)
    except CompositionError as e:
        print(red(str(e)))
        return 1
    flip_note = ", flipped" if ws.get("flip") else ""
    print(bold(f"{ws['name']}  ") + dim(f"({ws.get('layout')}{flip_note})"))
    for s in slots:
        if s.empty:
            print(f"  slot {s.index + 1}: {dim('(empty — desktop gap)')}")
        else:
            print(f"  slot {s.index + 1}: {swatch(s.color)} {bold(s.name)}  "
                  f"{dim(s.target)}  {yellow(s.model)}")
    return 0


def cmd_launch(config: dict, args) -> int:
    ws = find_workspace(config, args.name)
    if not ws:
        print(red(f"No workspace named '{args.name}'"))
        print(dim("Available: ") + ", ".join(w["name"] for w in config.get("workspaces", [])))
        return 1
    try:
        slots = resolve_workspace(config, ws)
    except CompositionError as e:
        print(red(str(e)))
        return 1

    flip = bool(ws.get("flip"))
    if not any(not s.empty for s in slots):
        print(red("Nothing to launch — every slot is empty."))
        return 1
    # Pass the original layout + slots (empties included). The backend places each
    # filled slot at its real position, leaving empty slots as desktop gaps.
    layout = ws.get("layout", "single")
    inject = args.inject_color or config["settings"].get("injectColor", False)
    delay = config["settings"].get("colorDelay", 1.5)
    ws_name = "tl-" + ws["name"].lower().replace(" ", "-")
    flip_note = ", flipped" if flip else ""

    if args.dry_run:
        print(bold(f"DRY RUN — {ws['name']} ({layout}{flip_note}) on {platform.system()}"))
        print(dim(f"terminal = {backend.name()}   inject_color = {inject}"))
        for line in backend.describe(layout, slots, flip):
            print("  " + line)
        return 0

    if not backend.available():
        print(red(f"{backend.name()} not available."))
        print(dim("Install it: " + backend.install_hint()))
        return 1

    print(green(f"Launching {ws['name']} ({layout}{flip_note})…"))
    try:
        backend.launch(layout, slots, inject_color=inject,
                       workspace_name=ws_name, color_delay=delay, flip=flip)
    except RuntimeError as e:
        print(red(str(e)))
        return 1
    return 0


# ---- interactive helpers ----------------------------------------------------

def _ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        val = input(f"{cyan('?')} {prompt}{suffix}: ").strip()
        if val:
            return val
        if default is not None:
            return default


def _choose(prompt: str, options: list[tuple[str, str]], default_idx: int = 0) -> str:
    """options = list of (value, label). Returns chosen value."""
    print(f"{cyan('?')} {prompt}")
    for i, (_, label) in enumerate(options):
        marker = "›" if i == default_idx else " "
        print(f"   {marker} {bold(str(i + 1))}. {label}")
    while True:
        raw = input(f"   choose 1-{len(options)} [{default_idx + 1}]: ").strip()
        if not raw:
            return options[default_idx][0]
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        print(red("   invalid choice"))


def _choose_pane(config: dict, slot_no: int) -> dict | None:
    panes = list(config["panes"].items())
    opts = [("__empty__", dim("(leave empty)"))]
    opts += [(pid, f"{swatch(p.get('color','gray'))} {p.get('name', pid)}  "
                   f"{dim(p.get('target',''))}") for pid, p in panes]
    choice = _choose(f"Slot {slot_no} — assign a pane", opts, default_idx=0)
    if choice == "__empty__":
        return None
    model = _choose_model(config, config["panes"][choice].get("model"))
    slot = {"pane": choice}
    pane_default = config["panes"][choice].get("model") or config["settings"]["defaultModel"]
    if model != pane_default:
        slot["model"] = model
    return slot


def _choose_model(config: dict, current: str | None) -> str:
    models = config.get("models", [])
    default = current or config["settings"].get("defaultModel", "opus")
    opts = [(m["id"], f"{m['label']}  {dim(m['id'])}") for m in models]
    default_idx = next((i for i, (mid, _) in enumerate(opts) if mid == default), 0)
    return _choose("Model", opts, default_idx=default_idx)


def _compose_workspace(config: dict, existing: dict | None = None) -> dict:
    name = _ask("Workspace name", existing.get("name") if existing else None)
    layout = _choose("Layout", [
        ("single", "Single  ■            — one pane, full screen"),
        ("split", "Split   ■■          — two panes, side by side"),
        ("combo", "Combo   █|▪▪        — one full pane + two stacked"),
        ("quad", "Quad    ■■/■■        — four panes, 2×2 grid"),
    ], default_idx=1 if not existing else
       {"single": 0, "split": 1, "combo": 2, "quad": 3}.get(existing.get("layout"), 1))

    slots = []
    for i in range(LAYOUT_CAPACITY[layout]):
        slots.append(_choose_pane(config, i + 1))
    ws = {"name": name, "layout": layout, "slots": slots}
    if layout in ("split", "combo"):  # horizontal flip only means anything here
        default_flip = "y" if (existing and existing.get("flip")) else "n"
        if _ask("Flip horizontally? (y/n)", default_flip).lower().startswith("y"):
            ws["flip"] = True
    return ws


def cmd_new(config: dict, path: Path, args) -> int:
    if not config.get("panes"):
        print(yellow("No panes configured yet — let's create one first.\n"))
        _interactive_pane(config)
    ws = _compose_workspace(config)
    if find_workspace(config, ws["name"]):
        print(red(f"A workspace named '{ws['name']}' already exists. "
                  f"Use `edit` or pick another name."))
        return 1
    config["workspaces"].append(ws)
    cfg.save(path, config)
    print(green(f"\nSaved workspace '{ws['name']}'."))
    cmd_preview(config, argparse.Namespace(name=ws["name"]))
    return 0


def cmd_edit(config: dict, path: Path, args) -> int:
    ws = find_workspace(config, args.name)
    if not ws:
        print(red(f"No workspace named '{args.name}'"))
        return 1
    print(dim(f"Editing '{ws['name']}' — press enter to keep current values.\n"))
    updated = _compose_workspace(config, existing=ws)
    idx = config["workspaces"].index(ws)
    config["workspaces"][idx] = updated
    cfg.save(path, config)
    print(green(f"\nUpdated workspace '{updated['name']}'."))
    return 0


def cmd_delete(config: dict, path: Path, args) -> int:
    ws = find_workspace(config, args.name)
    if not ws:
        print(red(f"No workspace named '{args.name}'"))
        return 1
    confirm = input(f"Delete workspace '{ws['name']}'? [y/N] ").strip().lower()
    if confirm != "y":
        print(dim("Cancelled."))
        return 0
    config["workspaces"].remove(ws)
    cfg.save(path, config)
    print(green(f"Deleted '{ws['name']}'."))
    return 0


def _interactive_pane(config: dict) -> dict:
    name = _ask("Pane name (e.g. Home, Docs, Backend)")
    pid = name.strip().lower().replace(" ", "-")
    target = _ask("Target directory", "~")
    color = _choose("Color", [(k, f"{swatch(k)} {k}") for k in cfg.COLORS.keys()])
    model = _choose_model(config, None)
    pane = {"name": name, "color": color, "target": target, "model": model}
    config["panes"][pid] = pane
    return pane


def cmd_pane_new(config: dict, path: Path, args) -> int:
    _interactive_pane(config)
    cfg.save(path, config)
    print(green("Saved pane."))
    return 0


def cmd_logs(args) -> int:
    p = diag.log_path()
    print(bold(f"Log file: {p}"))
    if not p.exists():
        print(dim("(no log yet — run the GUI or a launch first)"))
        return 0
    print(diag.read_tail(args.lines))
    return 0


def cmd_init(config: dict, path: Path, args) -> int:
    if path.exists():
        print(dim(f"Config already exists at {path}"))
        return 0
    cfg.seed_from_example(path)
    print(green(f"Created starter config at {path}"))
    print(dim("Edit it, or run `terminal-launcher new` to compose interactively."))
    return 0


def cmd_restore(path: Path, args) -> int:
    """Re-apply this pane's identity after `/clear`. Machine-readable, tab-delimited
    output so the Claude Code `/restore` command can interpret it:
      DETECTED\\t<name>\\t<color>            — identity found (always printed on a hit)
      RESTORED\\t/color <c>  +  /rename <n>  — injection ran (exit 0)
      UNKNOWN\\t<name>=<color>\\t...          — cwd matched no pane (exit 2)
      ERROR\\t<message>                      — injection failed, e.g. no backend (exit 1)
    """
    from . import restore as restore_mod
    if not path.exists():
        print("UNKNOWN\t(no config)")
        return 2
    try:
        res = restore_mod.restore(path, detect_only=getattr(args, "detect_only", False))
    except Exception as e:  # backend missing, session unresolved, etc.
        print(f"ERROR\t{e}", file=sys.stderr)
        return 1
    if not res["ok"]:
        print("UNKNOWN\t" + "\t".join(f"{n}={c}" for n, c in res["panes"]))
        return 2
    print(f"DETECTED\t{res['name']}\t{res['color']}")
    if res["injected"]:
        print(f"RESTORED\t/color {res['color']}  +  /rename {res['name']}")
    return 0


# ---- argparse wiring --------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="terminal-launcher",
        description="Compose and launch tiled Claude Code sessions.")
    ap.add_argument("--config", type=str, default=None,
                    help="path to the workspaces config JSON")
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("list", help="list saved workspaces")
    sub.add_parser("panes", help="list configured panes")
    sub.add_parser("init", help="create a starter config")
    sub.add_parser("new", help="interactively compose a new workspace")
    sub.add_parser("pane-new", help="interactively add a pane")
    sub.add_parser("gui", help="open the visual composer (native window)")

    lg = sub.add_parser("logs", help="print the diagnostics log (path + recent lines)")
    lg.add_argument("--lines", type=int, default=120, help="trailing lines to show")

    pv = sub.add_parser("preview", help="text preview of a workspace")
    pv.add_argument("name")

    lp = sub.add_parser("launch", help="launch a workspace")
    lp.add_argument("name")
    lp.add_argument("--dry-run", action="store_true",
                    help="print what would launch, don't open anything")
    lp.add_argument("--inject-color", action="store_true",
                    help="type /color into each session (needs Accessibility)")

    ed = sub.add_parser("edit", help="interactively edit a workspace")
    ed.add_argument("name")
    dl = sub.add_parser("delete", help="delete a workspace")
    dl.add_argument("name")

    rs = sub.add_parser("restore",
                        help="re-apply this pane's /color + /rename (after Claude Code's /clear)")
    rs.add_argument("--detect-only", action="store_true",
                    help="print the detected identity without injecting")
    return ap


def _force_utf8_stdio() -> None:
    """Make stdout/stderr UTF-8 so our box-drawing / status glyphs survive.

    A Windows console defaults to cp1252, which has no `■` (the layout-preview
    block) — printing one raises UnicodeEncodeError and kills the command
    outright (`list` and `preview` were both fatal). Reconfiguring with
    errors='replace' makes output safe on every platform."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass  # not a reconfigurable stream — carry on rather than fail a command


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdio()
    # Breaks the inheritance chain: a pane launched by the bundle is already polluted,
    # so a launch run from *inside* one would pass it on to the next generation.
    backend.scrub_bundled_python_env()
    ap = build_parser()
    args = ap.parse_args(argv)
    path = Path(args.config).expanduser() if args.config else cfg.default_config_path()
    diag.setup()

    if not args.cmd:
        ap.print_help()
        return 0

    if args.cmd == "logs":
        return cmd_logs(args)

    if args.cmd == "restore":
        return cmd_restore(path, args)

    # Commands that must not fail on a missing config (they create/seed it):
    if args.cmd == "init":
        return cmd_init({}, path, args)
    if args.cmd == "gui":
        from . import gui
        return gui.run(path)
    if args.cmd in ("new", "pane-new"):
        config = _load_or_seed(path)
        return cmd_new(config, path, args) if args.cmd == "new" \
            else cmd_pane_new(config, path, args)

    config = _load_or_die(path)
    dispatch = {
        "list": lambda: cmd_list(config, args),
        "panes": lambda: cmd_panes(config, args),
        "preview": lambda: cmd_preview(config, args),
        "launch": lambda: cmd_launch(config, args),
        "edit": lambda: cmd_edit(config, path, args),
        "delete": lambda: cmd_delete(config, path, args),
    }
    try:
        return dispatch[args.cmd]()
    except KeyboardInterrupt:
        print("\n" + dim("Cancelled."))
        return 130
