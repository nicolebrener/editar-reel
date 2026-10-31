"""Full-screen b-roll: finds stock clips (Pixabay or Pexels) or prepares the person's own clips, for a `broll` insert.

    PY scripts/broll.py search <project> "calendar planner" [--n 8]
        Searches the stock site whose key is saved. Writes work/broll-<query>.jpg (numbered thumbnails) and prints
        one line per result: number, id, duration, size. Vertical clips come first. Look at the sheet and pick.
    PY scripts/broll.py get <project> <id> --name agenda [--start 2] [--dur 3]
        Downloads that clip (the id as search printed it: pb123 for Pixabay, px123 for Pexels) and leaves it as
        assets/broll/agenda.mp4 (2160x3840 if the source is 4K, else 1080x1920; 30 fps, SDR, no sound; a horizontal
        clip is cropped to the centre).
    PY scripts/broll.py prep <project> <file> --name pantalla [--start 12] [--dur 4] [--fit] [--crop w:h:x:y]
        The same for a local clip (a screen recording, the person's own b-roll). --fit keeps the whole frame
        (for horizontal clips like a screen recording) over a blurred copy of itself instead of cropping.

Then in reel.json:  {"type": "broll", "src": "assets/broll/agenda.mp4", "start": 8.4, "end": 10.2, "mode": "full"}

Keys (free) live in the skill folder, one line each and git-ignored, or in environment variables:
    .pixabay_key / PIXABAY_API_KEY   https://pixabay.com/api/docs/ (shown on that page once logged in)
    .pexels_key  / PEXELS_API_KEY    https://www.pexels.com/api/
`sh scripts/stock_key.sh pixabay` saves one without showing it. Clips from both are free to use without attribution.
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
PROVIDERS = {'pb': ('Pixabay', 'PIXABAY_API_KEY', '.pixabay_key', 'https://pixabay.com/api/docs/'),
             'px': ('Pexels', 'PEXELS_API_KEY', '.pexels_key', 'https://www.pexels.com/api/')}


def key_for(p):
    name, env, fname, _ = PROVIDERS[p]
    key = os.environ.get(env, '').strip()
    path = os.path.join(common.SKILL_DIR, fname)
    if not key and os.path.exists(path):
        key = open(path, encoding='utf-8').read().strip()
    return key


def provider():
    """The first stock site with a saved key (Pixabay, then Pexels)."""
    for p in PROVIDERS:
        if key_for(p):
            return p
    common.die('falta una clave de stock gratis: Pixabay (https://pixabay.com/api/docs/, logueada aparece en la '
               'página) o Pexels. Guardala con: sh scripts/stock_key.sh pixabay')


def fetch_json(url, headers=None):
    req = urllib.request.Request(url, headers=dict({'User-Agent': 'editar-reel'}, **(headers or {})))
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


# each provider: search -> [{id, duration, width, height, thumb}], file_url(id) -> best mp4 for a 9:16 frame (4K when there is one)
def pixabay_search(query, n):
    q = urllib.parse.urlencode({'key': key_for('pb'), 'q': query, 'per_page': max(3, min(n * 3, 200)),
                                'safesearch': 'true'})
    out = []
    for v in fetch_json(f'https://pixabay.com/api/videos/?{q}').get('hits', []):
        f = v['videos'].get('large') or v['videos'].get('medium') or {}
        if f.get('url'):
            out.append({'id': f'pb{v["id"]}', 'duration': v['duration'], 'width': f['width'], 'height': f['height'],
                        'thumb': f.get('thumbnail') or v['videos'].get('medium', {}).get('thumbnail')})
    return out


def pixabay_file(vid):
    hits = fetch_json(f'https://pixabay.com/api/videos/?{urllib.parse.urlencode({"key": key_for("pb"), "id": vid})}')
    if not hits.get('hits'):
        common.die(f'Pixabay no tiene el video {vid}')
    vs = hits['hits'][0]['videos']
    # a horizontal clip gets cropped to 9:16: the largest file keeps it sharp
    return next(vs[k]['url'] for k in ('large', 'medium', 'small', 'tiny') if vs.get(k, {}).get('url'))


def pexels_search(query, n):
    q = urllib.parse.urlencode({'query': query, 'orientation': 'portrait', 'size': 'medium', 'per_page': n})
    res = fetch_json(f'https://api.pexels.com/videos/search?{q}', {'Authorization': key_for('px')})
    return [{'id': f'px{v["id"]}', 'duration': v['duration'], 'width': v['width'], 'height': v['height'],
             'thumb': v['image']} for v in res.get('videos', [])]


def pexels_file(vid):
    video = fetch_json(f'https://api.pexels.com/videos/videos/{vid}', {'Authorization': key_for('px')})
    files = [f for f in video.get('video_files', []) if f.get('width') and f.get('height')
             and f['height'] >= f['width'] and f.get('file_type') == 'video/mp4']
    if not files:
        common.die(f'el video {vid} no tiene una versión vertical en mp4')
    big = [f for f in files if f['height'] >= common.VH] or [f for f in files if f['height'] >= H]
    return (min(big, key=lambda f: f['height']) if big else max(files, key=lambda f: f['height']))['link']


SEARCH = {'pb': pixabay_search, 'px': pexels_search}
FILE = {'pb': pixabay_file, 'px': pexels_file}


def cmd_search(a):
    project = common.project_dir(a.project)
    p = provider()
    vids = SEARCH[p](a.query, a.n)
    # vertical first, then the sharpest horizontal ones (they get cropped to the centre)
    vids.sort(key=lambda v: (v['height'] < v['width'], -v['height']))
    vids = vids[:a.n]
    if not vids:
        common.die(f'{PROVIDERS[p][0]} no encontró nada para "{a.query}": probá otras palabras (en inglés funciona mejor)')
    from PIL import Image, ImageDraw, ImageFont
    tw, th = 216, 384
    sheet = Image.new('RGB', (len(vids) * (tw + 8) + 8, th + 16), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(os.path.join(common.SKILL_DIR, 'assets', 'fonts', 'Inter-ExtraBold.ttf'), 34)
    except OSError:
        font = ImageFont.load_default()
    tmp = os.path.join(project, 'work', '_stock_thumb.jpg')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    for n, v in enumerate(vids, 1):
        download(v['thumb'], tmp)
        im = Image.open(tmp).convert('RGB')
        # show the 9:16 centre crop the reel will use
        s = max(tw / im.width, th / im.height)
        im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1))
        l, t = (im.width - tw) // 2, (im.height - th) // 2
        im = im.crop((l, t, l + tw, t + th))
        x = 8 + (n - 1) * (tw + 8)
        sheet.paste(im, (x, 8))
        draw.rectangle((x, 8, x + 52, 52), fill=(0, 0, 0))
        draw.text((x + 10, 10), str(n), fill=(255, 225, 77), font=font)
        v['n'] = n
    os.remove(tmp)
    out = os.path.join(project, 'work', f'broll-{slug(a.query)}.jpg')
    sheet.save(out, quality=85)
    common.write_json(out.replace('.jpg', '.json'), vids)
    for v in vids:
        kind = 'vertical' if v['height'] >= v['width'] else 'horizontal (se recorta al centro)'
        print(f'{v["n"]:2d}  id {v["id"]:<12} {v["duration"]:3d} s  {v["width"]}x{v["height"]}  {kind}')
    print(f'hoja ({PROVIDERS[p][0]}): {out}')


def normalize(src, dest, start, dur, fit, crop=None):
    """Any clip -> 9:16, 30 fps, SDR Rec.709, no sound: crops to fill, or with fit, sits on a blurred copy.
    crop "w:h:x:y" (pixels of the source) keeps only that part first: the readable bit of a screen recording.
    A source with 4K detail in the 9:16 frame stays 2160x3840; anything smaller is kept at 1080x1920 (the 4K
    render scales it up the same way, so a bigger file would add nothing)."""
    info = common.video_info(src)
    sw, sh = (int(v) for v in crop.split(':')[:2]) if crop else (info['width'], info['height'])
    W, H = (common.VW, common.VH) if min(sh, sw * 16 / 9) >= common.VH * 0.9 else (common.W, common.H)
    pre = ''
    if info['hdr']:
        lut = common.hdr_lut_path(common.load_config().get('hdrExposure', 0.62)).replace('\\', '/').replace(':', '\\:')
        pre = (f'scale=in_color_matrix=bt2020:in_range=tv,format=gbrp16le,lut3d=\'{lut}\','
               'scale=out_color_matrix=bt709:out_range=tv,')
    if crop:
        pre += f'crop={crop},'
    if fit:
        vf = (f'{pre}split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},'
              f'boxblur=40:2,eq=brightness=-0.08[bg];[b]scale={W - W // 18}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2')
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
    p, vid = (a.id[:2], a.id[2:]) if a.id[:2] in PROVIDERS else ('px', a.id)
    if not key_for(p):
        common.die(f'falta la clave de {PROVIDERS[p][0]}: sh scripts/stock_key.sh {PROVIDERS[p][0].lower()}')
    raw = os.path.join(project, 'work', f'stock-{p}{vid}.mp4')
    if not os.path.exists(raw):
        download(FILE[p](vid), raw)
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
