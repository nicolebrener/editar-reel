"""Paso 6b: screenshots of the composition at chosen times, tiled into one sheet to review.

    PY scripts/snap.py <project> 1.2,4.5,9.8,...      # times in seconds on the final timeline
    PY scripts/snap.py <project> auto                 # one frame per caption emphasis / insert / segment

Build with --safe first to see the red safe-zone guide in the frames. Writes work/snaps.jpg.
"""
import glob
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


def auto_times(project):
    reel = common.read_json(os.path.join(project, 'reel.json'), {})
    caps = common.read_json(os.path.join(project, 'captions.json'), [])
    segs = common.read_json(os.path.join(project, 'segments.json'))
    ts = [it['start'] + min(0.8, (it['end'] - it['start']) / 2) for it in reel.get('inserts', [])]
    ts += [g['start'] + 0.3 for g in caps if g.get('emph')]
    ts += [(s['start'] + s['end']) / 2 for s in segs]
    out = []
    for t in sorted(ts):
        if not out or t - out[-1] > 0.6:
            out.append(round(t, 2))
    return out[:24]


def main():
    if len(sys.argv) < 3:
        common.die('uso: snap.py <project> <t1,t2,...|auto>')
    project = common.project_dir(sys.argv[1])
    times = auto_times(project) if sys.argv[2] == 'auto' else [float(t) for t in sys.argv[2].split(',')]
    out_dir = os.path.join(project, 'work', 'snaps')
    shutil.rmtree(out_dir, ignore_errors=True)
    common.hf(['snapshot', '--at', ','.join(f'{t:.2f}' for t in times), '--no-end', '--describe', 'false',
               '-o', out_dir, project], cwd=project)
    shots = sorted(glob.glob(os.path.join(out_dir, '*.png')))
    if not shots:
        common.die('snapshot no generó imágenes')
    from PIL import Image, ImageDraw, ImageFont
    tw, th, cols = 270, 480, 6
    rows = (len(shots) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * (tw + 6) + 6, rows * (th + 40) + 6), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(os.path.join(common.SKILL_DIR, 'assets', 'fonts', 'Inter-SemiBold.ttf'), 22)
    for k, p in enumerate(shots):
        x, y = 6 + (k % cols) * (tw + 6), 6 + (k // cols) * (th + 40)
        sheet.paste(Image.open(p).convert('RGB').resize((tw, th)), (x, y + 34))
        label = f'{times[k]:.2f}s' if k < len(times) else os.path.basename(p)
        draw.text((x + 4, y + 4), label, fill=(255, 214, 10), font=font)
    out = os.path.join(project, 'work', 'snaps.jpg')
    sheet.save(out, quality=85)
    common.say(f'OK {out} ({len(shots)} frames)')


if __name__ == '__main__':
    main()
