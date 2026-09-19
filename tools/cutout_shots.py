#!/usr/bin/env python3
"""Cut the device out of each homepage screenshot, so it sits on the page
rather than on a cream card.

The renders were exported for the App Store, where a filled card is correct.
On dearnudges.com the page is #FAFAFD, a cool near-white, and the export pads
the device with #F3F1EA, a warm cream. Two off-whites that do not match read
as a visible rectangle behind every phone, and the 0.88 opacity on the two
side phones muddied it further. It is worse in dark mode, where a cream slab
sits on #1A1A1A.

So: keep the device, drop the padding.

The mask is built FROM THE BEZEL, not from the background colour. Two earlier
attempts failed on colour:

  A global "near cream is transparent" test punches holes through the middle
  of the UI, because the app's own background inside the screen is a warm
  off-white within a few units of the padding colour.

  Flood-filling inward from the border fixes that, but the export carries
  faint decorative arcs in the padding. The flood stops at them, leaving the
  arcs and the cream they enclose floating beside the phone. Keeping only the
  largest opaque component removes the free-floating ones, and keeps every arc
  that happens to touch the frame.

The device is a solid near-black rounded rectangle, which is unambiguous. So:
take the largest connected run of near-black pixels, that is the bezel; then
anything the background cannot reach from the edge of the canvas is inside the
screen. Bezel plus interior is the silhouette, exactly, with no colour
tolerance anywhere near the artwork.

Run:  python3 tools/cutout_shots.py
Then rebuild the site. Original exports are kept in img/_source/.
"""
import pathlib
from collections import deque
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMG = ROOT / "img"
SRC = IMG / "_source"
SHOTS = ["shot-01", "shot-02", "shot-03"]

DARK = 260     # sum of r+g+b still counted as bezel
PAD = 10       # transparent margin kept around the device, for the drop shadow


def flood(seed, passable, w, h):
    """4-connected fill from every seed index, through passable() indices."""
    seen = bytearray(w * h)
    q = deque()
    for i in seed:
        if passable(i) and not seen[i]:
            seen[i] = 1
            q.append(i)
    while q:
        i = q.popleft()
        x, y = i % w, i // w
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h:
                j = ny * w + nx
                if not seen[j] and passable(j):
                    seen[j] = 1
                    q.append(j)
    return seen


def cutout(im):
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()

    dark = bytearray(w * h)
    for y in range(h):
        row = y * w
        for x in range(w):
            p = px[x, y]
            if p[0] + p[1] + p[2] < DARK:
                dark[row + x] = 1

    # Largest connected dark region: the bezel.
    seen = bytearray(w * h)
    bezel, best = None, 0
    for i in range(w * h):
        if not dark[i] or seen[i]:
            continue
        comp = flood([i], lambda j: dark[j] and not seen[j], w, h)
        idx = [j for j in range(w * h) if comp[j]]
        for j in idx:
            seen[j] = 1
        if len(idx) > best:
            bezel, best = comp, len(idx)

    # Everything the outside can reach without crossing the bezel is padding;
    # everything else that is not bezel is the screen.
    border = [x for x in range(w)] + [(h - 1) * w + x for x in range(w)] \
        + [y * w for y in range(h)] + [y * w + w - 1 for y in range(h)]
    outside = flood(border, lambda j: not bezel[j], w, h)

    for y in range(h):
        row = y * w
        for x in range(w):
            if outside[row + x]:
                px[x, y] = (0, 0, 0, 0)

    l, t, r, b = im.getbbox()
    return im.crop((max(0, l - PAD), max(0, t - PAD),
                    min(w, r + PAD), min(h, b + PAD)))


def main():
    SRC.mkdir(exist_ok=True)
    for name in SHOTS:
        png = IMG / f"{name}.png"
        keep = SRC / f"{name}.png"
        if not keep.exists():          # first run: preserve the original export
            keep.write_bytes(png.read_bytes())
        out = cutout(Image.open(keep))
        out.save(png, "PNG", optimize=True)
        out.save(IMG / f"{name}.webp", "WEBP", quality=88, method=6)
        print(f"{name}: {out.size[0]}x{out.size[1]}  "
              f"png {png.stat().st_size // 1024} kB  "
              f"webp {(IMG / f'{name}.webp').stat().st_size // 1024} kB")


if __name__ == "__main__":
    main()
