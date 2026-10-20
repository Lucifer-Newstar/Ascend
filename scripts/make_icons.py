"""Render the ASCEND logo (the two triangles from the sidebar) into app icons.

    python scripts/make_icons.py      # needs Pillow

Writes apps/desktop/build/icon.png (512 px) and icon.ico (16-256 px), which
electron-builder picks up from `buildResources: build`. Re-run after a logo change.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps" / "desktop" / "build"
BG = (10, 14, 21, 255)  # --color-bg
ACCENT = (34, 211, 238, 255)  # --color-accent
SIZE = 1024  # draw large, downsample for clean edges


def draw() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = SIZE // 6
    d.rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=r, fill=BG)
    # Same geometry as the 32x32 SVG in Layout.tsx: outer M16 3 L29 28 H3 Z, inner M16 13 L22 25 H10 Z.
    s = SIZE / 32
    outer = [(16 * s, 3 * s), (29 * s, 28 * s), (3 * s, 28 * s)]
    inner = [(16 * s, 13 * s), (22 * s, 25 * s), (10 * s, 25 * s)]
    # Stroke = accent triangle with a background triangle inset by the stroke width
    # (clean mitred corners, unlike a thick polyline).
    d.polygon(outer, fill=ACCENT)
    d.polygon(inset(outer, 2.4 * s), fill=BG)
    # Inner triangle at 35 % accent over the background, as in the SVG (opacity .35).
    d.polygon(
        inner,
        fill=tuple(round(b + 0.35 * (a - b)) for a, b in zip(ACCENT[:3], BG[:3], strict=True))
        + (255,),
    )
    return img


def inset(tri: list[tuple[float, float]], by: float) -> list[tuple[float, float]]:
    """Shrink a triangle towards its incentre so every edge moves in by `by` pixels."""
    (ax, ay), (bx, by_), (cx, cy) = tri
    a = ((bx - cx) ** 2 + (by_ - cy) ** 2) ** 0.5
    b = ((ax - cx) ** 2 + (ay - cy) ** 2) ** 0.5
    c = ((ax - bx) ** 2 + (ay - by_) ** 2) ** 0.5
    p = a + b + c
    ix, iy = (a * ax + b * bx + c * cx) / p, (a * ay + b * by_ + c * cy) / p
    area = abs((bx - ax) * (cy - ay) - (cx - ax) * (by_ - ay)) / 2
    r = 2 * area / p  # inradius
    k = (r - by) / r
    return [(ix + (x - ix) * k, iy + (y - iy) * k) for x, y in tri]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    big = draw()
    big.resize((512, 512), Image.LANCZOS).save(OUT / "icon.png")
    big.resize((256, 256), Image.LANCZOS).save(
        OUT / "icon.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"wrote {OUT / 'icon.png'} and {OUT / 'icon.ico'}")


if __name__ == "__main__":
    main()
