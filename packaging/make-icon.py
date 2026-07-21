"""Regenerate the app icon — master PNG + Windows .ico + macOS .icns, from one source.

    python packaging/make-icon.py

Writes all three so the two platforms can never drift apart:

    packaging/icon.png          1024px master
    packaging/windows/app.ico   multi-size (16-256) — Start Menu shortcut + PyInstaller
    packaging/icon.icns         multi-size — the py2app bundle

Cross-platform: pure Pillow, no pyobjc/Quartz and no `iconutil`, so it runs on the Mac
or the PC. (The .icns is written directly — it's just a container of PNG-encoded
entries — which is what lets Windows regenerate the macOS icon too.)

The mark: a dark squircle holding the **combo** layout — one full-height pane on the
left, two stacked on the right, in the pane palette. Deliberately asymmetric; a
symmetric 2x2 grid of coloured squares reads as a generic tech logo, not as this app.
"""
import io
import struct
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent

S = 4                       # supersample factor, downscaled at the end for clean edges
W = 1024                    # master size
BG = (14, 14, 22, 255)      # dark squircle
BLUE = (91, 141, 239, 255)
ORANGE = (209, 162, 79, 255)
GREEN = (138, 154, 79, 255)

PAD, RAD = 80, 210          # squircle inset + corner radius
IN, SPAN, GAP = 214, 596, 40
CELL = (SPAN - GAP) // 2    # 278
CR = 58                     # pane corner radius


def render() -> Image.Image:
    im = Image.new("RGBA", (W * S, W * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def pane(x, y, w, h, color, r=CR):
        d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S],
                            radius=r * S, fill=color)

    pane(PAD, PAD, W - 2 * PAD, W - 2 * PAD, BG, r=RAD)      # squircle
    pane(IN, IN, CELL, SPAN, BLUE)                            # full-height left
    pane(IN + CELL + GAP, IN, CELL, CELL, ORANGE)             # right top
    pane(IN + CELL + GAP, IN + CELL + GAP, CELL, CELL, GREEN)  # right bottom
    return im.resize((W, W), Image.LANCZOS)


def write_icns(img: Image.Image, path: Path) -> None:
    """Write a modern (PNG-entry) .icns container by hand.

    Format: 'icns' + total length, then per entry: 4-byte OSType + 4-byte length
    (inclusive of the 8-byte header) + PNG bytes. No `iconutil` needed."""
    entries = [(b"ic11", 32), (b"ic12", 64), (b"ic07", 128), (b"ic13", 256),
               (b"ic08", 256), (b"ic14", 512), (b"ic09", 512), (b"ic10", 1024)]
    blob = b""
    for ostype, size in entries:
        buf = io.BytesIO()
        img.resize((size, size), Image.LANCZOS).save(buf, format="PNG")
        data = buf.getvalue()
        blob += ostype + struct.pack(">I", len(data) + 8) + data
    path.write_bytes(b"icns" + struct.pack(">I", len(blob) + 8) + blob)


def main() -> None:
    img = render()

    png = HERE / "icon.png"
    img.save(png)
    print("wrote", png)

    ico = HERE / "windows" / "app.ico"
    ico.parent.mkdir(parents=True, exist_ok=True)
    img.save(ico, format="ICO", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    print("wrote", ico)

    icns = HERE / "icon.icns"
    write_icns(img, icns)
    print("wrote", icns)


if __name__ == "__main__":
    main()
