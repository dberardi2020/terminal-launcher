"""The visual composer — a fleeting native window (pywebview) over the shared core.

No web server: pywebview renders local HTML in the OS's native WebView and bridges
button clicks straight into the same core the CLI uses (`config` + `wezterm`). The
window IS the app — close it and the process exits. Launch quits the window behind
you: the fleeting open → launch → gone behavior.

The UI (web/builder.html) is a gallery of workspace cards + a live composer
(click-a-cell slot editor) + inline pane management. Everything it reads and writes
goes through this `Api` to the one `workspaces.json`. See docs/decisions/0003.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path

from . import config as cfg
from . import wezterm
from .config import COLORS, LAYOUT_CAPACITY, color_hex
from .model import CompositionError, compact, resolve_workspace

WEB = Path(__file__).resolve().parent / "web"


def _slugify(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


def _inherit_login_path() -> None:
    """Give the process the login shell's PATH.

    Apps launched from the Dock/Finder inherit a minimal PATH (no /opt/homebrew/bin),
    so `wezterm`/`claude` aren't found. Merge in the login shell's PATH plus the usual
    Homebrew/user bin dirs so the bundled .app behaves like a terminal launch. Safe to
    call when already run from a terminal — the merge is idempotent.
    """
    dirs: list[str] = []
    shell = os.environ.get("SHELL", "/bin/zsh")
    try:
        out = subprocess.run([shell, "-lic", "echo $PATH"],
                             capture_output=True, text=True, timeout=5)
        lines = [ln for ln in out.stdout.splitlines() if ln.strip()]
        if lines:
            dirs = [d for d in lines[-1].split(os.pathsep) if d]
    except Exception:
        pass
    for d in ("/opt/homebrew/bin", "/opt/homebrew/sbin", "/usr/local/bin",
              os.path.expanduser("~/.local/bin")):
        if d not in dirs:
            dirs.append(d)
    existing = [d for d in os.environ.get("PATH", "").split(os.pathsep) if d]
    os.environ["PATH"] = os.pathsep.join(existing + [d for d in dirs if d not in existing])


class Api:
    """The JS↔Python bridge. Methods are callable as `window.pywebview.api.*`."""

    def __init__(self, path: Path):
        self.path = path
        self._window = None

    def bind(self, window) -> None:
        self._window = window

    # -- helpers --------------------------------------------------------------

    def _load(self) -> dict:
        return cfg.load(self.path)

    def _find_ws(self, config: dict, name: str) -> int:
        lname = (name or "").strip().lower()
        for i, ws in enumerate(config.get("workspaces", [])):
            if ws.get("name", "").lower() == lname:
                return i
        return -1

    def _normalize_slots(self, layout: str, slots: list | None) -> list:
        """Pad/trim a wire-format slot list to the layout's capacity.
        Wire form: [{"pane": id, "model": id} | null, ...]."""
        cap = LAYOUT_CAPACITY.get(layout, 1)
        slots = list(slots or [])
        out = []
        for i in range(cap):
            s = slots[i] if i < len(slots) else None
            if isinstance(s, dict) and s.get("pane"):
                clean = {"pane": s["pane"]}
                if s.get("model"):
                    clean["model"] = s["model"]
                out.append(clean)
            else:
                out.append(None)
        return out

    # -- reads ----------------------------------------------------------------

    def get_state(self) -> dict:
        config = self._load()
        settings = config["settings"]
        default_model = settings.get("defaultModel", "opus")

        panes = {}
        for pid, p in config.get("panes", {}).items():
            color = p.get("color", "gray")
            panes[pid] = {
                "name": p.get("name", pid), "color": color,
                "hex": color_hex(color), "target": p.get("target", "~"),
                "model": p.get("model") or default_model,
            }

        workspaces = []
        for ws in config.get("workspaces", []):
            layout = ws.get("layout", "single")
            raw = self._normalize_slots(layout, ws.get("slots"))
            slots = []
            for s in raw:
                if s is None:
                    slots.append(None)
                else:
                    # model = the explicit override, or null for "Default" (inherit
                    # the pane's own default). The editor shows a Default chip for null.
                    slots.append({"pane": s["pane"], "model": s.get("model")})
            workspaces.append({"name": ws["name"], "layout": layout,
                               "slots": slots, "flip": bool(ws.get("flip"))})

        return {
            "panes": panes,
            "models": config.get("models", []),
            "colors": [{"name": n, "hex": h} for n, h in COLORS.items()],
            "workspaces": workspaces,
            "settings": settings,
            "wezterm": wezterm.available(),
            "defaultModel": default_model,
        }

    # -- workspace mutations --------------------------------------------------

    def save_workspace(self, name: str, layout: str, slots: list,
                       original: str | None = None, flip: bool = False) -> dict:
        config = self._load()
        name = (name or "").strip()
        if not name:
            return {"ok": False, "error": "Name required"}
        record = {"name": name, "layout": layout,
                  "slots": self._normalize_slots(layout, slots)}
        if flip:  # only stored when set, so single/quad configs stay clean
            record["flip"] = True

        idx = self._find_ws(config, original) if original else -1
        clash = self._find_ws(config, name)
        if idx >= 0:  # update existing (possibly renamed)
            if clash >= 0 and clash != idx:
                return {"ok": False, "error": f"'{name}' already exists"}
            config["workspaces"][idx] = record
        else:  # create new
            if clash >= 0:
                return {"ok": False, "error": f"'{name}' already exists"}
            config["workspaces"].append(record)
        cfg.save(self.path, config)
        return {"ok": True, "name": name}

    def delete_workspace(self, name: str) -> dict:
        config = self._load()
        idx = self._find_ws(config, name)
        if idx < 0:
            return {"ok": False, "error": f"No workspace '{name}'"}
        config["workspaces"].pop(idx)
        cfg.save(self.path, config)
        return {"ok": True}

    def duplicate_workspace(self, name: str) -> dict:
        config = self._load()
        idx = self._find_ws(config, name)
        if idx < 0:
            return {"ok": False, "error": f"No workspace '{name}'"}
        import json
        copy = json.loads(json.dumps(config["workspaces"][idx]))
        base = copy["name"] + " copy"
        new = base
        n = 2
        while self._find_ws(config, new) >= 0:
            new = f"{base} {n}"; n += 1
        copy["name"] = new
        config["workspaces"].insert(idx + 1, copy)
        cfg.save(self.path, config)
        return {"ok": True, "name": new}

    def move_workspace(self, name: str, direction: int) -> dict:
        config = self._load()
        i = self._find_ws(config, name)
        if i < 0:
            return {"ok": False, "error": f"No workspace '{name}'"}
        j = i + (1 if direction > 0 else -1)
        wss = config["workspaces"]
        if 0 <= j < len(wss):
            wss[i], wss[j] = wss[j], wss[i]
            cfg.save(self.path, config)
        return {"ok": True}

    def reorder_workspace(self, name: str, position: str) -> dict:
        """Jump a workspace to the 'front' or 'end' of the gallery order."""
        config = self._load()
        i = self._find_ws(config, name)
        if i < 0:
            return {"ok": False, "error": f"No workspace '{name}'"}
        wss = config["workspaces"]
        ws = wss.pop(i)
        wss.insert(0, ws) if position == "front" else wss.append(ws)
        cfg.save(self.path, config)
        return {"ok": True}

    # -- pane mutations (edit the config from within) -------------------------

    def save_pane(self, pane: dict, original_id: str | None = None) -> dict:
        config = self._load()
        name = (pane.get("name") or "").strip()
        if not name:
            return {"ok": False, "error": "Pane name required"}
        pid = original_id or _slugify(name)
        if not original_id and pid in config["panes"]:
            return {"ok": False, "error": f"Pane id '{pid}' already exists"}
        config["panes"][pid] = {
            "name": name,
            "color": pane.get("color", "gray"),
            "target": (pane.get("target") or "~").strip(),
            "model": pane.get("model") or config["settings"].get("defaultModel", "opus"),
        }
        cfg.save(self.path, config)
        return {"ok": True, "id": pid}

    def delete_pane(self, pane_id: str) -> dict:
        config = self._load()
        if pane_id not in config["panes"]:
            return {"ok": False, "error": "No such pane"}
        # refuse if any workspace still references it
        used = [w["name"] for w in config["workspaces"]
                for s in w.get("slots", []) if isinstance(s, dict) and s.get("pane") == pane_id]
        if used:
            return {"ok": False, "error": f"In use by: {', '.join(sorted(set(used)))}"}
        del config["panes"][pane_id]
        cfg.save(self.path, config)
        return {"ok": True}

    # -- pickers --------------------------------------------------------------

    def pick_directory(self, start: str | None = None) -> dict:
        """Open the OS-native folder chooser; return the picked path (~-collapsed).

        Returns {"ok": True, "path": ...} on selection, {"ok": False} on cancel
        (or if the dialog can't open). Home is re-collapsed to ~ for tidy configs.
        """
        if self._window is None:
            return {"ok": False}
        import webview  # lazy — same GUI stack the window came from
        init = os.path.expanduser(start or "~")
        if not os.path.isdir(init):
            init = os.path.expanduser("~")
        try:
            result = self._window.create_file_dialog(
                webview.FOLDER_DIALOG, directory=init)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        if not result:
            return {"ok": False}
        path = result[0] if isinstance(result, (list, tuple)) else result
        home = os.path.expanduser("~")
        if path == home or path.startswith(home + os.sep):
            path = "~" + path[len(home):]
        return {"ok": True, "path": path}

    # -- launch ---------------------------------------------------------------

    def _toast(self, message: str, is_error: bool = False) -> None:
        """Push a toast into the page (used from the launch worker thread)."""
        if self._window is None:
            return
        try:
            self._window.evaluate_js(
                f"toast({json.dumps(message)}, null, {str(is_error).lower()})")
        except Exception:
            pass

    def launch(self, comp: dict, close_after: bool = True) -> dict:
        """Launch a composition {name?, layout, slots} — saved or ad-hoc.

        Validation is synchronous (so bad input returns an error to JS instantly),
        but the actual WezTerm spawn — which sleeps for color-injection timing —
        runs on a BACKGROUND thread. Doing it on the GUI thread would beachball the
        window, and calling `destroy()` from inside a JS-API call deadlocks; a
        worker thread avoids both and closes the window cleanly when done.
        """
        config = self._load()
        if not wezterm.available():
            return {"ok": False, "error": "WezTerm not found on PATH."}
        layout = comp.get("layout", "single")
        flip = bool(comp.get("flip"))
        ws = {"name": comp.get("name") or "adhoc", "layout": layout,
              "slots": self._normalize_slots(layout, comp.get("slots"))}
        try:
            slots = resolve_workspace(config, ws)
        except CompositionError as e:
            return {"ok": False, "error": str(e)}
        if not any(not s.empty for s in slots):
            return {"ok": False, "error": "Nothing to launch — every slot is empty."}

        # Partial layouts compact: empty slots are dropped and the filled panes
        # tile with the layout that fits their count (no shell panes). See #6.
        layout, slots = compact(slots)
        settings = config["settings"]
        ws_name = "tl-" + _slugify(ws["name"])

        def worker() -> None:
            try:
                wezterm.launch(
                    layout, slots,
                    inject_color=settings.get("injectColor", False),
                    workspace_name=ws_name,
                    color_delay=settings.get("colorDelay", 1.5),
                    flip=flip,
                )
            except RuntimeError as e:
                self._toast(f"Launch failed: {e}", True)
                return
            if close_after:
                # Fleeting: the launcher goes away once the launch is fully handed
                # off. The WezTerm GUI + Claude sessions are independent processes
                # already spawned above, so they survive us exiting. os._exit is
                # deliberate — pywebview's window.destroy() is unreliable from a
                # non-managed thread in this build, and the process IS the app.
                os._exit(0)

        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}


def run(path: Path | None = None) -> int:
    import webview  # lazy import so the CLI doesn't hard-depend on the GUI stack

    _inherit_login_path()  # Dock-launched apps get a stripped PATH — restore it first
    path = path or cfg.default_config_path()
    if not path.exists():
        cfg.seed_from_example(path)

    html = (WEB / "builder.html").read_text(encoding="utf-8")
    api = Api(path)
    window = webview.create_window(
        "Terminal Launcher", html=html, js_api=api,
        width=1180, height=760, min_size=(760, 560), maximized=True,
    )
    api.bind(window)
    webview.start()
    return 0
