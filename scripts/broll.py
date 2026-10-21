"""Full-screen b-roll: finds stock clips on Pexels or prepares the person's own clips, ready for a `broll` insert.

    PY scripts/broll.py search <project> "calendar planner" [--n 8]
        Searches Pexels for vertical clips. Writes work/broll-<query>.jpg (numbered thumbnails) and prints
        one line per result: number, Pexels id, duration, size. Look at the sheet and pick.
    PY scripts/broll.py get <project> <pexels id> --name agenda [--start 2] [--dur 3]
        Downloads that clip and leaves it as assets/broll/agenda.mp4 (1080x1920, 30 fps, SDR, no sound).
    PY scripts/broll.py prep <project> <file> --name pantalla [--start 12] [--dur 4] [--fit] [--crop w:h:x:y]
        The same for a local clip (a screen recording, the person's own b-roll). --fit keeps the whole frame
        (for horizontal clips like a screen recording) over a blurred copy of itself instead of cropping.

Then in reel.json:  {"type": "broll", "src": "assets/broll/agenda.mp4", "start": 8.4, "end": 10.2, "mode": "full"}

The Pexels key (free, from https://www.pexels.com/api/) is read from the PEXELS_API_KEY environment variable or
from the file .pexels_key in the skill folder (git-ignored). Pexels clips are free to use without attribution.
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

W, H, FPS = common.W, common.H, common.FPS
KEY_FILE = os.path.join(common.SKILL_DIR, '.pexels_key')


def pexels_key():
    key = os.environ.get('PEXELS_API_KEY', '').strip()
    if not key and os.path.exists(KEY_FILE):
        key = open(KEY_FILE, encoding='utf-8').read().strip()
    if not key:
        common.die('falta la clave de Pexels: sacala gratis en https://www.pexels.com/api/ y guardala en '
                   f'{KEY_FILE} (una línea, solo la clave)')
    return key


def api(path, params):
    url = f'https://api.pexels.com/{path}?{urllib.parse.urlencode(params)}'
    req = urllib.request.Request(url, headers={'Authorization': pexels_key(), 'User-Agent': 'editar-reel'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))


def download(url, dest):
    req = urllib.request.Request(url, headers={'User-Agent': 'editar-reel'})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, 'wb') as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:40] or 'clip'


def cmd_search(a):
    project = common.project_dir(a.project)
    res = api('videos/search', {'query': a.query, 'orientation': 'portrait', 'size': 'medium',
                                'per_page': a.n})
    vids = res.get('videos', [])
    if not vids:
        common.die(f'Pexels no encontró nada para "{a.query}": probá otras palabras (en inglés funciona mejor)')
    from PIL import Image, ImageDraw, ImageFont
    tw, th = 216, 384
    sheet = Image.new('RGB', (len(vids) * (tw + 8) + 8, th + 16), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(os.path.join(common.SKILL_DIR, 'assets', 'fonts', 'Inter-ExtraBold.ttf'), 34)
    except OSError:
        font = ImageFont.load_default()
    tmp = os.path.join(project, 'work', '_pexels_thumb.jpg')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    rows = []
    for n, v in enumerate(vids, 1):
        download(v['image'], tmp)
        im = Image.open(tmp).convert('RGB')
        im = im.resize((tw, int(im.height * tw / im.width))).crop((0, 0, tw, th))
        x = 8 + (n - 1) * (tw + 8)
        sheet.paste(im, (x, 8))
        draw.rectangle((x, 8, x + 52, 52), fill=(0, 0, 0))
        draw.text((x + 10, 10), str(n), fill=(255, 225, 77), font=font)
        rows.append({'n': n, 'id': v['id'], 'duration': v['duration'], 'size': f'{v["width"]}x{v["height"]}',
                     'url': v['url']})
    os.remove(tmp)
    out = os.path.join(project, 'work', f'broll-{slug(a.query)}.jpg')
    sheet.save(out, quality=85)
    common.write_json(out.replace('.jpg', '.json'), rows)
    for r in rows:
        print(f'{r["n"]:2d}  id {r["id"]:<10} {r["duration"]:3d} s  {r["size"]}')
    print(f'hoja: {out}')


def best_file(video):
    """The portrait file closest to 1080x1920 (the largest when none is that big)."""
    files = [f for f in video.get('video_files', []) if f.get('width') and f.get('height')
             and f['height'] >= f['width'] and f.get('file_type') == 'video/mp4']
    if not files:
        common.die(f'el video {video["id"]} no tiene una versión vertical en mp4')
    big = [f for f in files if f['height'] >= H]
    return min(big, key=lambda f: f['height']) if big else max(files, key=lambda f: f['height'])


def normalize(src, dest, start, dur, fit, crop=None):
    """Any clip -> 1080x1920, 30 fps, SDR Rec.709, no sound: crops to fill, or with fit, sits on a blurred copy.
    crop "w:h:x:y" (pixels of the source) keeps only that part first: the readable bit of a screen recording."""
    info = common.video_info(src)
    pre = ''
    if info['hdr']:
        lut = common.hdr_lut_path(common.load_config().get('hdrExposure', 0.62)).replace('\\', '/').replace(':', '\\:')
        pre = (f'scale=in_color_matrix=bt2020:in_range=tv,format=gbrp16le,lut3d=\'{lut}\','
               'scale=out_color_matrix=bt709:out_range=tv,')
    if crop:
        pre += f'crop={crop},'
    if fit:
        vf = (f'{pre}split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},'
              f'boxblur=40:2,eq=brightness=-0.08[bg];[b]scale={W - 60}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2')
    else:
        vf = f'{pre}scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}'
    vf += f',fps={FPS},setsar=1,format=yuv420p,setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709'
    cmd = ['ffmpeg', '-v', 'error', '-y']
    if start:
        cmd += ['-ss', f'{start:.3f}']
    if dur:
        cmd += ['-t', f'{dur:.3f}']
    cmd += ['-i', src, '-filter_complex' if fit else '-vf', vf, '-an', '-c:v', 'libx264', '-preset', 'fast',
            '-crf', '17', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', dest]
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    common.run(cmd)
    print(f'OK {os.path.relpath(dest, os.path.dirname(os.path.dirname(dest)))}  '
          f'{common.video_info(dest)["duration"]:.2f} s')


def cmd_get(a):
    project = common.project_dir(a.project)
    video = api(f'videos/videos/{a.id}', {})
    raw = os.path.join(project, 'work', f'pexels-{a.id}.mp4')
    if not os.path.exists(raw):
        download(best_file(video)['link'], raw)
    normalize(raw, os.path.join(project, 'assets', 'broll', f'{slug(a.name)}.mp4'), a.start, a.dur, False)


def cmd_prep(a):
    project = common.project_dir(a.project)
    src = common.expand(a.file)
    if not os.path.isfile(src):
        common.die(f'no existe: {src}')
    normalize(src, os.path.join(project, 'assets', 'broll', f'{slug(a.name)}.mp4'), a.start, a.dur, a.fit, a.crop)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('search')
    s.add_argument('project')
    s.add_argument('query')
    s.add_argument('--n', type=int, default=8)
    for name in ('get', 'prep'):
        p = sub.add_parser(name)
        p.add_argument('project')
        p.add_argument('id' if name == 'get' else 'file')
        p.add_argument('--name', required=True)
        p.add_argument('--start', type=float, default=0)
        p.add_argument('--dur', type=float, default=0)
        if name == 'prep':
            p.add_argument('--fit', action='store_true')
            p.add_argument('--crop', help='w:h:x:y del original: solo esa parte (lo que se lee de una grabación)')
    a = ap.parse_args()
    {'search': cmd_search, 'get': cmd_get, 'prep': cmd_prep}[a.cmd](a)


if __name__ == '__main__':
    main()
