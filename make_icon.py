"""
Generates PhotoNamer.icns — photo frame + location pin + name tag.
Run with:  .venv/bin/python make_icon.py
"""
import math
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

SIZE = 1024


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def make_background(size) -> Image.Image:
    """Dark warm-slate gradient with macOS rounded corners."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    top    = (38, 48, 62)
    bottom = (20, 26, 36)
    px = img.load()
    for y in range(size):
        t = y / (size - 1)
        r, g, b = lerp_color(top, bottom, t)
        for x in range(size):
            px[x, y] = (r, g, b, 255)
    radius = int(size * 0.225)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size - 1, size - 1], radius=radius, fill=255
    )
    img.putalpha(mask)
    return img


def draw_photo_frame(d: ImageDraw.ImageDraw, s: int):
    """White Polaroid-style photo frame, upper-centre of icon."""
    fw = s * 0.58
    fh = s * 0.52
    fx = s / 2 - fw / 2
    fy = s * 0.10
    fr = s * 0.04

    # Drop shadow
    shadow_img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_img)
    sd.rounded_rectangle(
        [fx + s * 0.012, fy + s * 0.018, fx + fw + s * 0.012, fy + fh + s * 0.018],
        radius=fr, fill=(0, 0, 0, 90),
    )
    return fx, fy, fw, fh, fr, shadow_img


def draw_scene(d: ImageDraw.ImageDraw, fx, fy, fw, fh, fr, s):
    """Sky + mountain landscape inside the photo frame."""
    mg = s * 0.022          # inner margin
    ix0 = fx + mg; iy0 = fy + mg
    ix1 = fx + fw - mg; iy1 = fy + fh - mg
    iw = ix1 - ix0; ih = iy1 - iy0
    ir = fr * 0.55

    # Sky (clip to inner rounded rect via separate layer done in caller)
    d.rounded_rectangle([ix0, iy0, ix1, iy1], radius=ir, fill=(105, 175, 230))

    # Gradient sky — brighter at top
    for row in range(int(ih * 0.65)):
        t = row / (ih * 0.65)
        r, g, b = lerp_color((145, 205, 255), (80, 150, 215), t)
        y = iy0 + row
        d.line([(ix0 + 2, y), (ix1 - 2, y)], fill=(r, g, b))

    # Ground
    ground_y = iy0 + ih * 0.62
    d.rectangle([ix0 + 2, ground_y, ix1 - 2, iy1 - 2], fill=(90, 140, 80))

    # Mountains
    mx = ix0 + iw * 0.5
    m_peaks = [
        (ix0 + iw * 0.18, iy0 + ih * 0.62, ix0 + iw * 0.52, iy0 + ih * 0.22, ix0 + iw * 0.72, iy0 + ih * 0.62),
        (ix0 + iw * 0.50, iy0 + ih * 0.62, ix0 + iw * 0.76, iy0 + ih * 0.34, ix1 - 2,          iy0 + ih * 0.62),
    ]
    colors = [(155, 125, 105), (130, 105, 90)]
    snow_colors = [(235, 242, 255), (220, 232, 248)]
    for pts, col, snow in zip(m_peaks, colors, snow_colors):
        x0, y0, px_, py, x1, y1 = pts
        d.polygon([(x0, y0), (px_, py), (x1, y1)], fill=col)
        # Snow cap
        snow_h = (y1 - py) * 0.28
        d.polygon([
            (px_ - (x1 - x0) * 0.10, py + snow_h),
            (px_, py),
            (px_ + (x1 - x0) * 0.10, py + snow_h),
        ], fill=snow)

    # Sun
    scx = ix0 + iw * 0.80
    scy = iy0 + ih * 0.15
    sr = iw * 0.075
    d.ellipse([scx - sr, scy - sr, scx + sr, scy + sr], fill=(255, 220, 70))


def draw_location_pin(d: ImageDraw.ImageDraw, cx, cy, r, s):
    """Bold red teardrop pin."""
    pin_red   = (220, 55, 45)
    pin_dark  = (170, 30, 25)
    tail_y    = cy + r * 1.70

    # Body ellipse
    d.ellipse([cx - r, cy - r, cx + r, cy + r * 0.75], fill=pin_red)
    # Tail triangle
    d.polygon([
        (cx - r * 0.42, cy + r * 0.45),
        (cx + r * 0.42, cy + r * 0.45),
        (cx, tail_y),
    ], fill=pin_red)
    # Subtle dark outline
    d.ellipse([cx - r, cy - r, cx + r, cy + r * 0.75],
              outline=pin_dark, width=max(2, int(r * 0.06)))
    # White inner circle
    ir = r * 0.40
    icy = cy - r * 0.10
    d.ellipse([cx - ir, icy - ir, cx + ir, icy + ir], fill=(255, 255, 255))
    # Highlight
    hr = ir * 0.38
    d.ellipse([cx - ir * 0.55 - hr, icy - ir * 0.55 - hr,
               cx - ir * 0.55 + hr, icy - ir * 0.55 + hr],
              fill=(255, 255, 255, 160))


def draw_tag(d: ImageDraw.ImageDraw, tx, ty, tw, th, s):
    """Cream name-tag with punched hole and text lines."""
    tr = s * 0.022
    cream = (245, 238, 218)
    d.rounded_rectangle([tx, ty, tx + tw, ty + th], radius=tr, fill=cream)
    # Outline
    d.rounded_rectangle([tx, ty, tx + tw, ty + th], radius=tr,
                        outline=(200, 190, 165), width=max(1, int(s * 0.005)))
    # Hole
    hole_r = s * 0.018
    hx = tx + tw * 0.50
    hy = ty + th * 0.22
    d.ellipse([hx - hole_r, hy - hole_r, hx + hole_r, hy + hole_r],
              fill=(180, 170, 148))
    # Text lines
    lw = max(2, int(s * 0.020))
    lx0 = tx + tw * 0.14; lx1 = tx + tw * 0.86
    ly1 = ty + th * 0.52
    ly2 = ty + th * 0.72
    d.line([(lx0, ly1), (lx1, ly1)],       fill=(130, 115, 90), width=lw)
    d.line([(lx0, ly2), (lx0 + (lx1 - lx0) * 0.62, ly2)],
           fill=(160, 145, 118), width=int(lw * 0.8))


def generate_icon():
    print("Drawing icon…")
    s = SIZE

    base = make_background(s)

    # ---- Photo frame -------------------------------------------------------
    fx, fy, fw, fh, fr, shadow_img = draw_photo_frame(ImageDraw.Draw(base), s)
    base = Image.alpha_composite(base, shadow_img)
    d = ImageDraw.Draw(base)

    # White frame
    d.rounded_rectangle([fx, fy, fx + fw, fy + fh], radius=fr, fill=(255, 255, 255))

    # Scene inside
    draw_scene(d, fx, fy, fw, fh, fr, s)

    # ---- String from frame to tag ------------------------------------------
    string_x = fx + fw * 0.34
    string_y0 = fy + fh
    string_y1 = fy + fh + s * 0.095
    str_w = max(2, int(s * 0.009))
    d.line([(string_x, string_y0), (string_x, string_y1)],
           fill=(200, 185, 155), width=str_w)

    # ---- Name tag ----------------------------------------------------------
    tw = fw * 0.50; th = fh * 0.22
    tx = string_x - tw / 2
    ty = string_y1
    draw_tag(d, tx, ty, tw, th, s)

    # ---- Location pin (overlapping bottom-right of photo) ------------------
    pin_r = s * 0.130
    pcx = fx + fw * 0.80
    pcy = fy + fh * 0.56
    draw_location_pin(d, pcx, pcy, pin_r, s)

    # ---- Subtle vignette ---------------------------------------------------
    vig = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vig)
    r = int(s * 0.225)
    vd.rounded_rectangle([0, 0, s - 1, s - 1], radius=r,
                         outline=(0, 0, 0, 70), width=int(s * 0.05))
    vig = vig.filter(ImageFilter.GaussianBlur(s * 0.04))
    base = Image.alpha_composite(base, vig)

    # ---- Build iconset -----------------------------------------------------
    iconset = Path("PhotoNamer.iconset")
    iconset.mkdir(exist_ok=True)

    specs = [
        ("icon_16x16.png",        16),
        ("icon_16x16@2x.png",     32),
        ("icon_32x32.png",        32),
        ("icon_32x32@2x.png",     64),
        ("icon_128x128.png",     128),
        ("icon_128x128@2x.png",  256),
        ("icon_256x256.png",     256),
        ("icon_256x256@2x.png",  512),
        ("icon_512x512.png",     512),
        ("icon_512x512@2x.png", 1024),
    ]

    for filename, px in specs:
        resized = base.resize((px, px), Image.LANCZOS)
        resized.save(iconset / filename)
        print(f"  {filename}")

    print("Running iconutil…")
    subprocess.run(["iconutil", "-c", "icns", str(iconset)], check=True)
    shutil.rmtree(iconset)
    print("PhotoNamer.icns created.")


if __name__ == "__main__":
    generate_icon()
