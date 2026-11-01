"""Stickers: cuts sticker sheets (several stickers on a plain background) into one transparent PNG per sticker.

    PY scripts/stickers.py cut <pack> <image> [<image> ...] [--tol 22]
        Removes the plain background around the stickers (only where it touches the edge, so white highlights inside
        a chrome star stay), splits what is left into separate stickers and saves them as
        ~/reel-stickers/<pack>/<pack>-01.png ... plus ~/reel-stickers/<pack>/sheet.jpg to look at and rename them.
    PY scripts/stickers.py list
        Every pack and sticker available.

Stickers live outside the repo (~/reel-stickers): packs downloaded from Pinterest or bought from a designer are
not ours to publish. In reel.json a sticker is an image insert whose src is "sticker:<pack>/<name>":
    {"type": "image", "src": "sticker:girly/heart-01", "mode": "sticker", "start": 3.2, "end": 5, "x": 760, "y": 300,
     "w": 220, "rot": -8}
build.py copies it into the project's assets/stickers/.
"""
import argparse
import collections
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

STICKERS_DIR = os.path.expanduser('~/reel-stickers')


def resolve(src):
    """'sticker:pack/name' -> path of the PNG, or None."""
    if not src.startswith('sticker:'):
        return None
    p = os.path.join(STICKERS_DIR, src[len('sticker:'):])
    return p if p.endswith('.png') else p + '.png'


def background_mask(rgb, tol):
    """True where the pixel is background: close to the edge colour AND connected to the edge."""
    import numpy as np
    h, w, _ = rgb.shape
    edge = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]).astype(np.int32)
    bg = np.median(edge, axis=0)
    dist = np.abs(rgb.astype(np.int32) - bg).max(axis=2)
    near = dist <= tol
    seen = np.zeros((h, w), bool)
    q = collections.deque()
    for x in range(w):
        for y in (0, h - 1):
            if near[y, x] and not seen[y, x]:
                seen[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if near[y, x] and not seen[y, x]:
                seen[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and near[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                q.append((ny, nx))
    return seen, dist


def components(mask, step=3, gap=3):
    """The separate shapes in mask: (label grid, [(id, box)]), computed on a 1/step grid; shapes closer than gap px
    merge into one."""
    import numpy as np
    small = mask[::step, ::step]
    h, w = small.shape
    lab = np.zeros((h, w), np.int32)
    boxes, n = [], 0
    reach = max(1, gap // step)
    for sy in range(h):
        for sx in range(w):
            if small[sy, sx] and not lab[sy, sx]:
                n += 1
                lab[sy, sx] = n
                q = collections.deque([(sy, sx)])
                y0, y1, x0, x1, area = sy, sy, sx, sx, 0
                while q:
                    y, x = q.popleft()
                    area += 1
                    y0, y1, x0, x1 = min(y0, y), max(y1, y), min(x0, x), max(x1, x)
                    for ny in range(max(0, y - reach), min(h, y + reach + 1)):
                        for nx in range(max(0, x - reach), min(w, x + reach + 1)):
                            if small[ny, nx] and not lab[ny, nx]:
                                lab[ny, nx] = n
                                q.append((ny, nx))
                boxes.append((n, (x0 * step, y0 * step, (x1 + 1) * step, (y1 + 1) * step, area * step * step)))
    return lab, boxes


def cut(a):
    import numpy as np
    from PIL import Image
    out_dir = os.path.join(STICKERS_DIR, a.pack)
    os.makedirs(out_dir, exist_ok=True)
    n = len(glob.glob(os.path.join(out_dir, f'{a.pack}-*.png')))
    made = []
    for path in a.images:
        im = Image.open(path).convert('RGB')
        rgb = np.asarray(im)
        bg, dist = background_mask(rgb, a.tol)
        # soft edge: pixels just past the tolerance fade in, so there is no white halo around the sticker
        alpha = np.clip((dist - a.tol) / (a.tol * 1.5), 0, 1)
        alpha = np.where(bg, 0.0, np.maximum(alpha, 0.0))
        alpha[~bg & (dist > a.tol * 2.5)] = 1.0
        solid = alpha > 0.5
        h, w = solid.shape
        step = 3
        lab, comps = components(solid, step)
        for cid, (x0, y0, x1, y1, area) in comps:
            if area < h * w * 0.002 or min(x1 - x0, y1 - y0) < 24:
                continue    # specks, stray text
            pad = 4
            x0, y0, x1, y1 = max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad)
            # only this shape's own pixels (a neighbour inside the box stays out), grown a little for the soft edge
            own = np.repeat(np.repeat(lab == cid, step, axis=0), step, axis=1)[:h, :w]
            grown = own.copy()
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-2, 0), (2, 0), (0, -2), (0, 2)):
                grown |= np.roll(np.roll(own, dy * step, axis=0), dx * step, axis=1)
            a_ = alpha[y0:y1, x0:x1] * grown[y0:y1, x0:x1]
            rgba = np.dstack([rgb[y0:y1, x0:x1], (a_ * 255).astype(np.uint8)])
            n += 1
            name = os.path.join(out_dir, f'{a.pack}-{n:02d}.png')
            Image.fromarray(rgba, 'RGBA').save(name)
            made.append(name)
    sheet(out_dir)
    common.say(f'OK {len(made)} stickers en {out_dir}  (hoja: {os.path.join(out_dir, "sheet.jpg")})')


def sheet(out_dir):
    """Contact sheet of a pack on a checkerboard, with names, to choose and rename stickers."""
    from PIL import Image, ImageDraw, ImageFont
    files = sorted(glob.glob(os.path.join(out_dir, '*.png')))
    if not files:
        return
    cell, cols = 220, 6
    rows = (len(files) + cols - 1) // cols
    img = Image.new('RGB', (cols * cell, rows * (cell + 28)), (236, 236, 236))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(os.path.join(common.SKILL_DIR, 'assets', 'fonts', 'Inter-SemiBold.ttf'), 15)
    for i, f in enumerate(files):
        x, y = (i % cols) * cell, (i // cols) * (cell + 28)
        for cy in range(0, cell, 20):
            for cx in range(0, cell, 20):
                if (cx // 20 + cy // 20) % 2:
                    d.rectangle([x + cx, y + cy, x + cx + 19, y + cy + 19], fill=(214, 214, 214))
        s = Image.open(f)
        s.thumbnail((cell - 16, cell - 16))
        img.paste(s, (x + (cell - s.width) // 2, y + (cell - s.height) // 2), s)
        d.text((x + 6, y + cell + 4), os.path.splitext(os.path.basename(f))[0], fill=(40, 40, 40), font=font)
    img.save(os.path.join(out_dir, 'sheet.jpg'), quality=88)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('cut')
    c.add_argument('pack')
    c.add_argument('images', nargs='+')
    c.add_argument('--tol', type=int, default=22)
    sub.add_parser('list')
    a = ap.parse_args()
    if a.cmd == 'cut':
        cut(a)
    else:
        for pack in sorted(glob.glob(os.path.join(STICKERS_DIR, '*'))):
            names = sorted(os.path.splitext(os.path.basename(f))[0] for f in glob.glob(os.path.join(pack, '*.png')))
            common.say(f'{os.path.basename(pack)}: {", ".join(names)}')


if __name__ == '__main__':
    main()
