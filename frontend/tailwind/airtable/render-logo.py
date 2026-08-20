#!/usr/bin/env python3
"""Rasterise the Learno mark to PNG.

The mark is authored as SVG (frontend/public/learning.svg,
frontend/src/components/Icons/LMSLogo.vue), but several consumers need PNG:
the favicon, the Apple touch icon, and the Frappe desk app icon. No SVG
rasteriser is available in this toolchain and pulling one in for three static
files is not worth a dependency, so the geometry — a rounded tile, an "L", and
a dot — is drawn directly here and written out with a minimal PNG encoder.

Keep the shapes in step with learning.svg if the mark changes.

Usage: python3 tailwind/airtable/render-logo.py
"""
import struct
import zlib
from pathlib import Path

# Airtable blueBright, the kit's primary action colour.
BLUE = (0x2D, 0x7F, 0xF9)
WHITE = (0xFF, 0xFF, 0xFF)

# Source geometry, in the SVG's 80x79 user-space units.
VB_W, VB_H = 80.0, 79.0
# The tile radius follows the design system, not the old mark: Airtable is a
# small-radius system (3px controls, 6px cards, 8px app frame), and the previous
# 21-unit radius on an 80-unit tile read as a squircle. 10 units is ~8px at
# favicon size — the app-frame radius, the largest the kit uses anywhere.
TILE_RADIUS = 10.0
L_X, L_Y, L_W, L_STEM_H = 26.5, 19.5, 11.2, 29.4
L_FOOT_W, L_FOOT_H = 29.0, 10.6
DOT_CX, DOT_CY, DOT_R, DOT_ALPHA = 53.5, 26.5, 6.6, 0.85

SS = 4  # supersampling factor per axis; 16 samples per output pixel


def inside_rounded_rect(x: float, y: float, w: float, h: float, r: float) -> bool:
    if x < 0 or y < 0 or x > w or y > h:
        return False
    # Only the four corner boxes need the radius test.
    cx = r if x < r else (w - r if x > w - r else None)
    cy = r if y < r else (h - r if y > h - r else None)
    if cx is None or cy is None:
        return True
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def inside_l(x: float, y: float) -> bool:
    stem = L_X <= x <= L_X + L_W and L_Y <= y <= L_Y + L_STEM_H + L_FOOT_H
    foot = L_X <= x <= L_X + L_FOOT_W and L_Y + L_STEM_H <= y <= L_Y + L_STEM_H + L_FOOT_H
    return stem or foot


def inside_dot(x: float, y: float) -> bool:
    return (x - DOT_CX) ** 2 + (y - DOT_CY) ** 2 <= DOT_R * DOT_R


def sample(x: float, y: float) -> tuple[int, int, int, int]:
    """Colour + coverage at one point in user space. Returns (r,g,b,a) 0-255."""
    if not inside_rounded_rect(x, y, VB_W, VB_H, TILE_RADIUS):
        return (0, 0, 0, 0)
    if inside_l(x, y):
        return WHITE + (255,)
    if inside_dot(x, y):
        # Composite the 85%-opacity dot over the blue tile.
        a = DOT_ALPHA
        return tuple(round(WHITE[i] * a + BLUE[i] * (1 - a)) for i in range(3)) + (255,)
    return BLUE + (255,)


def render(size: int) -> list[bytes]:
    """Render `size`x`size` RGBA rows, supersampled for antialiasing."""
    rows = []
    # Preserve the source aspect by fitting the 80x79 box into a square.
    scale = max(VB_W, VB_H) / size
    off_x = (max(VB_W, VB_H) - VB_W) / 2
    off_y = (max(VB_W, VB_H) - VB_H) / 2
    for py in range(size):
        row = bytearray()
        for px in range(size):
            acc = [0, 0, 0, 0]
            for sy in range(SS):
                uy = (py + (sy + 0.5) / SS) * scale - off_y
                for sx in range(SS):
                    ux = (px + (sx + 0.5) / SS) * scale - off_x
                    r, g, b, a = sample(ux, uy)
                    # Premultiply so partially covered edges blend correctly.
                    acc[0] += r * a
                    acc[1] += g * a
                    acc[2] += b * a
                    acc[3] += a
            n = SS * SS
            alpha = acc[3] / n
            if alpha < 0.5:
                row += bytes((0, 0, 0, 0))
            else:
                row += bytes(
                    (
                        min(255, round(acc[0] / acc[3])),
                        min(255, round(acc[1] / acc[3])),
                        min(255, round(acc[2] / acc[3])),
                        min(255, round(alpha)),
                    )
                )
        rows.append(bytes(row))
    return rows


def write_png(path: Path, size: int) -> None:
    rows = render(size)
    # Filter type 0 (None) on every scanline.
    raw = b"".join(b"\x00" + r for r in rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    Path(path).write_bytes(png)
    print(f"  {path}  {size}x{size}  {len(png)} bytes")


if __name__ == "__main__":
    # .../frontend/tailwind/airtable/render-logo.py -> repo root is three levels up.
    root = Path(__file__).resolve().parents[3]
    print("rendering Learno mark:")
    for rel, size in [
        ("frontend/public/favicon.png", 144),
        ("frontend/public/manifest/apple-icon-180.png", 180),
        ("lms/public/images/lms-logo.png", 469),
    ]:
        write_png(root / rel, size)
