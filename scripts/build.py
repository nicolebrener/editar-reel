"""Paso 6: writes <project>/index.html (the HyperFrames composition) from the project's JSON files.

    PY scripts/build.py <project> [--safe]      # --safe draws the Reels safe zone in red (for snapshots only)

Inputs:  aroll.mp4, segments.json, captions.json, reel.json (optional),
         assets/cutout.webm (needed only when a title is "behind": true)

reel.json, the creative plan. Every key is optional; times are seconds on the final timeline:
{
  "captions": {"y": 1130, "size": 92, "emphSize": 150},
  "autoZoom": true,                 # quick punch-in on every emphasis caption
  "zooms":   [{"start": 3.2, "end": 5.0, "scale": 1.18, "ox": 0.5, "oy": 0.35}],
  "flashes": [6.4],                 # white flash at these times (good on a hard topic change)
  "music":   {"src": "assets/music.mp3", "volume": 0.08},
  "inserts": [
    {"type": "title",    "text": "INVERSIÓN CREATIVA", "start": 4.1, "end": 6.0, "behind": true, "color": 0},
    {"type": "broll",    "src": "assets/x.mp4", "start": 7, "end": 9.5, "mode": "full", "mediaStart": 0},
    {"type": "image",    "src": "assets/y.png", "start": 10, "end": 12, "mode": "card", "y": 260, "w": 620, "rot": -4},
    {"type": "image",    "src": "assets/z.png", "start": 12, "end": 13, "mode": "sticker", "x": 760, "y": 900, "w": 300},
    {"type": "scribble", "text": "chef kiss", "start": 14, "end": 15.5, "x": 120, "y": 420, "rot": -8},
    {"type": "profile",  "start": 20, "end": 23.5, "followers": "12,4 mil", "posts": "210"},
    {"type": "webm",     "src": "assets/insert.webm", "start": 16, "end": 19, "x": 90, "y": 260, "w": 900}
  ],
  "sfx": {"gain": 1.0}              # 0 turns all sound effects off
}
colors: an integer picks config colors.accents[n]; a "#hex" string is used as is.
"""
import glob
import hashlib
import html
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anims  # noqa: E402
import scenes  # noqa: E402
import common  # noqa: E402

W, H, SAFE = common.W, common.H, common.SAFE
SFX_BASE = {'pop': 0.32, 'click': 0.45, 'ding': 0.22, 'rise': 0.25, 'bass': 0.4, 'whoosh': 0.3}


_SFX_LEN = {}


def sfx_length(name):
    if name not in _SFX_LEN:
        p = os.path.join(common.SKILL_DIR, 'assets', 'sfx', name + '.mp3')
        _SFX_LEN[name] = float(common.ffprobe(p)['format']['duration'])
    return _SFX_LEN[name]


def esc(s):
    return html.escape(str(s), quote=True)


def color(cfg, c, default=None):
    acc = cfg['colors']['accents']
    if c is None:
        return default or acc[0]
    if isinstance(c, int):
        return acc[c % len(acc)]
    return c


def clipped_cutout(project, clips):
    """Copy of cutout.webm where everything above y is transparent during each (start, end, y) window.

    Done with ffmpeg, not CSS: HyperFrames composites video frames itself and ignores clip-path."""
    src = os.path.join(project, 'assets', 'cutout.webm')
    if not clips:
        return 'assets/cutout.webm'
    key = hashlib.md5(json.dumps(['v2', os.path.getmtime(src), clips]).encode()).hexdigest()[:8]
    name = f'assets/cutout-{key}.webm'
    out = os.path.join(project, name)
    if not os.path.exists(out):
        for old in glob.glob(os.path.join(project, 'assets', 'cutout-*.webm')):
            os.remove(old)
        # y is in composition pixels; the cutout can be 4K. Outside the title windows the cutout goes fully
        # transparent: the person comes from aroll itself (no second compression on the face)
        k = media_size(src)[1] / H
        boxes = ','.join(f"drawbox=x=0:y=0:w=iw:h={round(y * k)}:color=black@0:t=fill:replace=1:"
                         f"enable='between(t,{s:.3f},{e:.3f})'" for s, e, y in clips)
        inside = '+'.join(f'between(t,{s:.3f},{e:.3f})' for s, e, _ in clips)
        boxes += f",drawbox=x=0:y=0:w=iw:h=ih:color=black@0:t=fill:replace=1:enable='not({inside})'"
        common.say('preparando el recorte para los títulos detrás de la cabeza (~1 min)')
        common.run(['ffmpeg', '-v', 'error', '-y', '-c:v', 'libvpx-vp9', '-i', src, '-vf',
                    f'format=yuva420p,{boxes}', '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-b:v', '0',
                    '-crf', '20', '-row-mt', '1', '-tile-columns', '2', '-deadline', 'good', '-cpu-used', '4',
                    '-an', out])
    return name


def media_size(path):
    try:
        info = common.ffprobe(path)
        v = next(s for s in info['streams'] if s['codec_type'] == 'video')
        return int(v['width']), int(v['height'])
    except Exception:  # noqa: BLE001
        return 1080, 1080


def fit_size(text, base, max_w=W - 2 * 60, ratio=0.6):
    """Font size so the longest word fits in max_w (Cal Sans averages ~0.6 em per letter)."""
    longest = max((len(w) for w in text.split()), default=1)
    return int(min(base, max_w / (longest * ratio)))


class Comp:
    def __init__(self, cfg, project, safe):
        self.cfg, self.project, self.safe = cfg, project, safe
        self.css, self.layers, self.tl, self.audio = [], {}, [], []
        self.n = 0
        self.clips = []   # (start, end, y): cutout transparent above y during that window

    def uid(self, p):
        self.n += 1
        return f'{p}{self.n}'

    def add(self, z, markup):
        self.layers.setdefault(z, []).append(markup)

    def anim(self, js):
        self.tl.append(js)

    def sfx(self, name, t, gain=1.0):
        g = self.cfg.get('_sfx_gain', 1.0) * gain
        if not name or g <= 0 or t < 0:
            return
        i = self.uid('sfx')
        d = sfx_length(name)
        self.audio.append(f'<audio id="{i}" src="assets/sfx/{name}.mp3" data-start="{t:.3f}" '
                          f'data-duration="{d:.3f}" data-track-index="{100 + len(self.audio)}" '
                          f'data-volume="{SFX_BASE.get(name, .3) * g:.3f}"></audio>')


# ---------------------------------------------------------------- captions
# Fonts for captions and titles (all OFL, in assets/fonts). ratio = average width of a lowercase letter in em, so
# fit_size can keep the longest word inside the frame; capitals run ~23 % wider (UPPER)
FONTS = {
    'cal':        {'family': "'Cal Sans'", 'weight': 400, 'ratio': 0.60, 'ls': '0.5px'},
    'inter':      {'family': "'Inter'", 'weight': 800, 'ratio': 0.62, 'ls': '-0.5px'},
    'montserrat': {'family': "'Montserrat'", 'weight': 900, 'ratio': 0.68, 'ls': '-0.5px'},
    'poppins':    {'family': "'Poppins'", 'weight': 800, 'ratio': 0.66, 'ls': '-0.5px'},
    'grotesk':    {'family': "'Space Grotesk'", 'weight': 700, 'ratio': 0.60, 'ls': '-0.5px'},
    'anton':      {'family': "'Anton'", 'weight': 400, 'ratio': 0.46, 'ls': '0.5px'},
    'bebas':      {'family': "'Bebas Neue'", 'weight': 400, 'ratio': 0.40, 'ls': '1px'},
    'dmserif':    {'family': "'DM Serif Display'", 'weight': 400, 'ratio': 0.55, 'ls': '0px'},
    'caveat':     {'family': "'Caveat'", 'weight': 700, 'ratio': 0.42, 'ls': '0px'},
    'montserrat-m': {'family': "'Montserrat'", 'weight': 500, 'ratio': 0.58, 'ls': '0px'},
    # MIRA's social font: licensed, so it is not in this repo; it comes from the editar-reel-mira skill next to this
    # one (MATTER_DIR). Without it the captions fall back to Inter
    'matter':      {'family': "'Matter'", 'weight': 600, 'ratio': 0.56, 'ls': '-0.01em'},
    'matter-bold': {'family': "'Matter'", 'weight': 700, 'ratio': 0.57, 'ls': '-0.02em'},
}
MATTER_DIR = os.path.join(os.path.dirname(common.SKILL_DIR), 'editar-reel-mira', 'assets', 'brand')
UPPER = 0.74 / 0.60
# no outline ever: a soft shadow, or a dark box behind the words
SHADOWS = {'soft': '0 4px 14px rgba(0,0,0,.55),0 2px 4px rgba(0,0,0,.45)',
           'light': '0 3px 18px rgba(0,0,0,.35),0 1px 3px rgba(0,0,0,.3)',
           'strong': '0 6px 26px rgba(0,0,0,.8),0 2px 6px rgba(0,0,0,.7)',
           'none': 'none', 'box': 'none'}
# the two base looks; every key can be overridden in reel.json "captions" (the studio does exactly that)
STYLES = {
    'pop':   {'font': 'cal', 'emphFont': 'cal', 'size': 92, 'emphSize': 150, 'color': None, 'emphColor': None,
              'case': 'asis', 'emphCase': 'upper', 'emphItalic': False, 'shadow': 'soft', 'anim': 'pop',
              'emphSfx': 'pop', 'y': 1240, 'curve': 0, 'tilt': 0, 'emphBox': None},
    'clean': {'font': 'inter', 'emphFont': 'inter', 'size': 80, 'emphSize': 130, 'color': '#FFFFFF',
              'emphColor': '#FFE14D', 'case': 'auto', 'emphCase': 'upper', 'emphItalic': True, 'shadow': 'light',
              'anim': 'soft', 'emphSfx': None, 'y': 1240, 'curve': 0, 'tilt': 0, 'emphBox': None},
}


def caption_style(opts, cfg):
    """The resolved caption look: the base style plus whatever reel.json overrides.
    color None = config colors.caption; emphColor None = emphasis colours rotate through config colors.accents."""
    st = dict(STYLES['clean' if opts.get('style') == 'clean' else 'pop'])
    st.update({k: v for k, v in opts.items() if k in st})
    st['style'] = 'clean' if opts.get('style') == 'clean' else 'pop'
    st['color'] = st['color'] or cfg['colors']['caption']
    for k in ('font', 'emphFont'):
        if st[k] not in FONTS:
            common.die(f'captions.{k}: no existe "{st[k]}" (hay: {", ".join(FONTS)})')
        if st[k].startswith('matter') and not os.path.exists(os.path.join(MATTER_DIR, 'Matter-Bold.otf')):
            common.say(f'captions.{k}: Matter no está (va en la skill editar-reel-mira); uso Inter')
            st[k] = 'inter'
    return st


def studio_values(reel, cfg):
    """What every studio control is set to, defaults included (scripts/studio.py, assets/studio/options.json)."""
    st = caption_style(reel.get('captions', {}), cfg)
    vals = {f'captions.{k}': v for k, v in st.items()}
    vals['captions.emphColor'] = reel.get('captions', {}).get('emphColor', st['emphColor'])
    vals.update({'titleFont': reel.get('titleFont', 'cal'), 'autoZoom': reel.get('autoZoom', True),
                 'sfx.gain': reel.get('sfx', {}).get('gain', 1.0)})
    return vals


def cased(t, mode, sentence_start=False):
    if mode == 'upper':
        return t.upper()
    if mode == 'lower' or (mode == 'auto' and sentence_start):
        return t.lower()
    return t


def ink_on(bg):
    """Black or white text for a coloured ground."""
    r, g, b = (int(bg.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return '#111115' if 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.5 else '#FFFFFF'


def arc_path(y, sag):
    """A circular arc across the frame whose middle is at height y and whose ends drop `sag` px."""
    x0, x1 = SAFE['left'] + 30, SAFE['right'] - 30
    half = (x1 - x0) / 2
    r = (half * half + sag * sag) / (2 * sag)
    return f'M{x0},{y + sag:.1f} A{r:.1f},{r:.1f} 0 0 1 {x1},{y + sag:.1f}', 2 * half + 8 / 3 * sag * sag / (2 * half)


def caption_css(st):
    f, ef = FONTS[st['font']], FONTS[st['emphFont']]
    css = ''
    if os.path.exists(os.path.join(MATTER_DIR, 'Matter-Bold.otf')):
        css += ''.join(f"@font-face{{font-family:'Matter';font-weight:{wt};src:url('assets/brand/Matter-{n}.otf') "
                       f"format('opentype')}}\n" for wt, n in ((600, 'SemiBold'), (700, 'Bold')))
    css += (f".w{{display:inline-block;font-family:{f['family']},sans-serif;font-weight:{f['weight']};line-height:1.02;"
           f"color:{st['color']};letter-spacing:{f['ls']};text-shadow:{SHADOWS.get(st['shadow'], SHADOWS['soft'])}}}\n"
           f".w.e{{font-family:{ef['family']},sans-serif;font-weight:{ef['weight']};"
           f"line-height:{0.95 if st['anim'] == 'pop' else 1};"
           f"letter-spacing:{ef['ls']};font-style:{'italic' if st['emphItalic'] else 'normal'}}}\n")
    if st['shadow'] == 'box' and not st['curve']:
        css += '.cap-in{background:rgba(12,12,12,.62);border-radius:24px;padding:4px 28px 12px}\n'
    # arched captions: SVG text on a path. Text shadows do not reach SVG text, so the shadow is a drop-shadow filter
    sh = {'soft': '0 4px 10px rgba(0,0,0,.5)', 'light': '0 3px 12px rgba(0,0,0,.3)',
          'strong': '0 5px 16px rgba(0,0,0,.75)'}.get(st['shadow'])
    css += ('.cap.arc{left:0;right:0;top:0;height:1920px;display:block}\n'
            '.cap.arc .cap-in{display:block}\n'
            f'.arcsvg{{position:absolute;left:0;top:0;overflow:visible{";filter:drop-shadow(" + sh + ")" if sh else ""}}}\n'
            '.arcsvg text{white-space:pre}.arcsvg tspan{fill:currentColor}\n'
            '.pill{display:inline-flex;flex-wrap:wrap;justify-content:center;gap:0 0.24em;padding:0.12em 0.42em 0.18em;'
            'border-radius:9999px;box-shadow:0 24px 48px -16px rgba(20,28,56,.45)}\n'
            '.pill .w{color:inherit !important;text-shadow:none}\n')
    return css


def build_captions(c, caps, st):
    cfg = c.cfg
    pop = st['anim'] == 'pop'
    for k, g in enumerate(caps):
        gid = f'cap-{esc(g["id"])}'
        end = g['end']
        if k + 1 < len(caps):   # never two captions on screen at once (hand edits can leave ends overlapping)
            end = min(end, caps[k + 1]['start'] - 1 / common.FPS)
        dur = max(0.1, end - g['start'])
        is_emph = bool(g.get('emph'))
        if is_emph:
            # a "#hex" in the group's emph wins (one colour per section), then the reel's emphColor, then the
            # accents in rotation
            own = g['emph'].get('color')
            col = own if isinstance(own, str) and own.startswith('#') else (st['emphColor'] or color(cfg, own))
            texts = [cased(w['t'], st['emphCase']) for w in g['words']]
            ratio = FONTS[st['emphFont']]['ratio'] * (UPPER if st['emphCase'] == 'upper' else 1)
            # the emphasis tilts and grows 6 %: keep it inside the safe zone
            fs = fit_size(' '.join(texts), st['emphSize'], max_w=W - 2 * 100, ratio=ratio)
            y = g.get('y') or (st['y'] - (30 if pop else 0))
            words = ''.join(f'<span class="w e" style="color:{col};font-size:{fs}px">{esc(t)}</span>' for t in texts)
            if st['emphBox'] == 'pill' and not st['curve']:
                words = f'<span class="pill" style="background:{col};color:{ink_on(col)}">{words}</span>'
        else:
            texts = [cased(w['t'], st['case'], w.get('ss')) for w in g['words']]
            ratio = FONTS[st['font']]['ratio'] * (UPPER if st['case'] == 'upper' else 1)
            fs = fit_size(' '.join(texts), st['size'], ratio=ratio)
            y = g.get('y') or st['y']
            words = ''.join(f'<span class="w" style="font-size:{fs}px">{esc(t)}</span>' for t in texts)
        if st['curve']:
            build_arc_caption(c, g, k, gid, dur, texts, is_emph, col if is_emph else None, y, st)
            continue
        c.add(8, f'<div id="{gid}" class="clip cap" data-start="{g["start"]:.3f}" data-duration="{dur:.3f}" '
                 f'data-track-index="8" style="top:{y}px"><div class="cap-in">{words}</div></div>')
        if st['emphBox'] == 'pill' and is_emph:
            c.anim(f'tl.fromTo("#{gid} .pill",{{scale:0.86,opacity:0}},{{scale:1,opacity:1,duration:0.22,'
                   f'ease:"power3.out"}},{g["start"]:.3f});')
        rot = ((k * 37) % 9 - 4) if is_emph else 0     # deterministic small tilt per emphasis
        for i, w in enumerate(g['words']):
            sel = f'#{gid} .w:nth-child({i + 1})'
            t = max(g['start'], min(w['s'], g['end'] - 0.1))
            if st['anim'] == 'none':
                c.anim(f'tl.fromTo("{sel}",{{opacity:0}},{{opacity:1,duration:0.04}},{t:.3f});')
            elif pop and is_emph:
                c.anim(f'tl.fromTo("{sel}",{{scale:0.25,rotation:{rot - 10},opacity:0}},'
                       f'{{scale:1,rotation:{rot},opacity:1,duration:0.24,ease:"back.out(3)"}},{t:.3f});')
            elif pop:
                c.anim(f'tl.fromTo("{sel}",{{scale:0.6,y:24,opacity:0}},'
                       f'{{scale:1,y:0,opacity:1,duration:0.13,ease:"back.out(2.4)"}},{t:.3f});')
            elif is_emph:
                c.anim(f'tl.fromTo("{sel}",{{scale:0.82,opacity:0}},'
                       f'{{scale:1,opacity:1,duration:0.2,ease:"power3.out"}},{t:.3f});')
            else:
                c.anim(f'tl.fromTo("{sel}",{{y:14,opacity:0}},{{y:0,opacity:1,duration:0.12,ease:"power2.out"}},'
                       f'{t:.3f});')
        if is_emph and pop:
            c.anim(f'tl.to("#{gid} .cap-in",{{scale:1.06,duration:{max(0.2, dur - 0.25):.3f},ease:"sine.inOut"}},'
                   f'{g["start"] + 0.24:.3f});')
        if is_emph and st['emphSfx']:
            c.sfx(st['emphSfx'], g['start'], 1.0 if pop else 0.6)


def build_arc_caption(c, g, k, gid, dur, texts, is_emph, col, y, st):
    """A caption bent along an arc (the "halo" over the head), with a small tilt of its own. Each word fades in
    when it is said (SVG text: fill-opacity, since transforms do not reach a tspan)."""
    path, length = arc_path(y, st['curve'])
    font = FONTS[st['emphFont'] if is_emph else st['font']]
    mode = st['emphCase'] if is_emph else st['case']
    chars = len(' '.join(texts)) * font['ratio'] * (UPPER if mode == 'upper' else 1)
    fs = int(min(st['emphSize'] if is_emph else st['size'], 0.9 * length / max(chars, 1)))
    tilt = st['tilt']
    rot = ((k * 53) % (2 * tilt + 1) - tilt) if tilt else 0
    own = f" style='color:{col}'" if col else ''
    spans = ''.join(f'<tspan class="w{" e" if is_emph else ""}"{own}>{" " if i else ""}{esc(t)}</tspan>'
                    for i, t in enumerate(texts))
    c.add(8, f'<div id="{gid}" class="clip cap arc" data-start="{g["start"]:.3f}" data-duration="{dur:.3f}" '
             f'data-track-index="8"><div class="cap-in" style="transform-origin:540px {y}px">'
             f'<svg class="arcsvg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><path id="{gid}-p" d="{path}" '
             f'fill="none"/><text font-size="{fs}" transform="rotate({rot} 540 {y})"><textPath href="#{gid}-p" '
             f'startOffset="50%" text-anchor="middle">{spans}</textPath></text></svg></div></div>')
    c.anim(f'tl.fromTo("#{gid} .cap-in",{{y:16,opacity:0}},{{y:0,opacity:1,duration:0.22,ease:"power2.out"}},'
           f'{g["start"]:.3f});')
    for i, w in enumerate(g['words']):
        t = max(g['start'], min(w['s'], g['end'] - 0.1))
        c.anim(f'tl.fromTo("#{gid} .w:nth-child({i + 1})",{{attr:{{"fill-opacity":0}}}},'
               f'{{attr:{{"fill-opacity":1}},duration:0.14,ease:"power1.out"}},{t:.3f});')
    if is_emph and st['emphSfx']:
        c.sfx(st['emphSfx'], g['start'], 0.6)


# ---------------------------------------------------------------- inserts
IG_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">'
           '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4.2"/>'
           '<circle cx="17.4" cy="6.6" r="1.1" fill="currentColor" stroke="none"/></svg>')


def ins_number(c, it):
    """A huge outlined numeral over the speaker ("1", "2", "3"): marks each point of a list."""
    i = c.uid('num')
    dur = it['end'] - it['start']
    fs = it.get('size', 760)
    c.add(6, f'<div id="{i}" class="clip num" data-start="{it["start"]:.3f}" data-duration="{dur:.3f}" '
             f'data-track-index="6" style="left:{it.get("x", 0)}px;top:{it.get("y", 560)}px;font-size:{fs}px;'
             f'-webkit-text-stroke:{it.get("stroke", 16)}px {it.get("color", "#FFFFFF")}">'
             f'<div class="num-in">{esc(it["text"])}</div></div>')
    c.anim(f'tl.fromTo("#{i} .num-in",{{scale:1.25,opacity:0}},{{scale:1,opacity:1,duration:0.3,ease:"power3.out"}},'
           f'{it["start"]:.3f});')
    c.anim(f'tl.to("#{i} .num-in",{{opacity:0,scale:0.95,duration:0.2}},{it["end"] - 0.2:.3f});'
           f'tl.set("#{i} .num-in",{{opacity:0}},{it["end"]:.3f});')
    c.sfx(it.get('sfx', 'whoosh'), it['start'] - 0.05, 0.6)


def ins_anim(c, it):
    """An animated line icon that illustrates what is being said (anims.py): it draws itself on, keeps a small
    loop going and fades out. `pos` "right"/"left" puts it beside the head; `x`/`y` place it by hand."""
    name = it['icon']
    if name not in anims.ICONS:
        common.die(f'anim: no existe el ícono "{name}" (hay: {", ".join(sorted(anims.ICONS))})')
    i = c.uid('anim')
    dur = it['end'] - it['start']
    size = it.get('size', 260)
    x = it.get('x', SAFE['left'] + 25 if it.get('pos') == 'left' else SAFE['right'] - size - 15)
    y = it.get('y', 780)
    fg = color(c.cfg, it.get('color'), '#FFFFFF')
    acc = color(c.cfg, it.get('accent'), c.cfg.get('_emph') or c.cfg['colors']['caption'])
    badge = it.get('style') == 'badge'
    if badge:
        fg = '#161616'
    label = f'<div class="anim-l">{esc(it["label"])}</div>' if it.get('label') else ''
    c.add(6, f'<div id="{i}" class="clip anim{" badge" if badge else ""}" data-start="{it["start"]:.3f}" '
             f'data-duration="{dur:.3f}" data-track-index="6" style="left:{x}px;top:{y}px;width:{size}px;'
             f'--fg:{fg};--acc:{acc}"><div class="anim-in"><svg viewBox="0 0 100 100">{anims.ICONS[name]}</svg>'
             f'</div>{label}</div>')
    t0 = it['start']
    c.anim(f'tl.fromTo("#{i} .anim-in",{{scale:0.6,opacity:0}},{{scale:1,opacity:1,duration:0.3,'
           f'ease:"back.out(2)"}},{t0:.3f});')
    c.anim(f'tl.fromTo("#{i} .d",{{strokeDashoffset:1,opacity:0}},{{strokeDashoffset:0,opacity:1,duration:0.5,ease:"power2.out",'
           f'stagger:0.08}},{t0 + 0.05:.3f});')
    c.anim(f'tl.fromTo("#{i} .p",{{scale:0,transformOrigin:"50% 50%"}},{{scale:1,duration:0.2,ease:"back.out(3)",'
           f'stagger:0.06}},{t0 + 0.4:.3f});')
    c.anim(f'tl.fromTo("#{i} .k",{{strokeDashoffset:1,opacity:0}},{{strokeDashoffset:0,opacity:1,duration:0.35,ease:"power2.out",'
           f'stagger:0.22}},{t0 + 0.55:.3f});')
    if label:
        c.anim(f'tl.fromTo("#{i} .anim-l",{{y:16,opacity:0}},{{y:0,opacity:1,duration:0.25}},{t0 + 0.3:.3f});')
    if name in anims.MOTION:
        sel, vars_, cycle = anims.MOTION[name]
        loop_from = t0 + 0.9
        n = int((it['end'] - 0.25 - loop_from) / cycle)
        if n >= 2:
            full_turn = 'rotation:360' in vars_
            reps = n - 1 if full_turn else (n // 2) * 2 - 1     # yoyo: an odd repeat count ends back at rest
            c.anim(f'tl.to("#{i} {sel}",Object.assign({vars_},{{duration:{cycle},repeat:{reps},'
                   f'yoyo:{"false" if full_turn else "true"}}}),{loop_from:.3f});')
    c.anim(f'tl.to("#{i}",{{opacity:0,scale:0.9,duration:0.2}},{it["end"] - 0.2:.3f});'
           f'tl.set("#{i}",{{opacity:0}},{it["end"]:.3f});')
    c.sfx(it.get('sfx', 'pop'), t0, 0.5)


def ins_scene(c, it):
    """A full-screen animated scene that explains what is being said (scenes.py): a chat, a calendar, a list..."""
    kind = it.get('kind')
    if kind not in scenes.KINDS:
        common.die(f'scene: no existe "{kind}" (hay: {", ".join(scenes.KINDS)})')
    i = c.uid('scn')
    dur = it['end'] - it['start']
    acc = color(c.cfg, it.get('accent'), c.cfg.get('_emph') or c.cfg['colors']['caption'])
    markup, js, times = scenes.KINDS[kind](i, it, acc)
    c.add(5, f'<div id="{i}" class="clip scn" data-start="{it["start"]:.3f}" data-duration="{dur:.3f}" '
             f'data-track-index="5" style="--acc:{acc}"><div class="scn-bg"></div>'
             f'<div class="scn-in">{markup}</div></div>')
    c.anim(f'tl.fromTo("#{i} .scn-in",{{scale:1.04,opacity:0}},{{scale:1,opacity:1,duration:0.25,'
           f'ease:"power2.out"}},{it["start"]:.3f});')
    for line in js:
        c.anim(line)
    c.sfx(it.get('sfx', 'whoosh'), it['start'] - 0.05, 0.6)
    for t in times:
        c.sfx(it.get('itemSfx', 'click'), t, 0.35)


def lit_aroll(project, cfg, lights):
    """aroll.mp4 with coloured lights baked onto the wall: each light is a soft-light glow over the frame, then the
    cutout goes back on top, so the face keeps its real colour. Baked with ffmpeg because HyperFrames composites
    video frames itself and ignores CSS blend modes (a CSS light shows in snapshots but not in the render).
    Light: {"type": "light", "start", "end", "color", "x", "y" (0-1, the lamp), "size" (% of the frame height),
            "strength" (0-1), "blend" (ffmpeg blend mode: overlay by default; softlight is much subtler)}"""
    from PIL import Image
    import numpy as np
    cut = os.path.join(project, 'assets', 'cutout.webm')
    if not os.path.exists(cut):
        common.die('las luces de fondo necesitan assets/cutout.webm: correr cutout.py primero')
    key = hashlib.md5(json.dumps([os.path.getmtime(os.path.join(project, 'aroll.mp4')), os.path.getmtime(cut),
                                  lights], sort_keys=True).encode()).hexdigest()[:8]
    name = f'assets/aroll-lit-{key}.mp4'
    out = os.path.join(project, name)
    if os.path.exists(out):
        return name
    for old in glob.glob(os.path.join(project, 'assets', 'aroll-lit-*.mp4')):
        os.remove(old)
    vw, vh = media_size(os.path.join(project, 'aroll.mp4'))   # the light is drawn at the video's own size (4K)
    yy, xx = np.mgrid[0:vh, 0:vw].astype(np.float32)
    inputs, chain, last = [], '[0:v]format=gbrp[b0];', 'b0'
    for k, it in enumerate(lights):
        rgb = np.array([int(color(cfg, it.get('color'), '#FF8A3D').lstrip('#')[j:j + 2], 16) for j in (0, 2, 4)],
                       np.float32)
        r = it.get('size', 80) / 100 * vh
        d = np.hypot(xx - it.get('x', 0.78) * vw, yy - it.get('y', 0.2) * vh)
        f = (np.clip(1 - d / r, 0, 1) ** 1.3 * it.get('strength', 0.9))[..., None]
        # soft-light against mid grey changes nothing: the glow is grey -> colour, strongest at the lamp
        img = (128 + (rgb - 128) * f).clip(0, 255).astype(np.uint8)
        png = os.path.join(project, 'work', f'_light{k}.png')
        Image.fromarray(img).save(png)
        inputs += ['-loop', '1', '-i', png]
        chain += (f'[{k + 2}:v]format=gbrp[l{k}];[{last}][l{k}]blend=all_mode={it.get('blend', 'overlay')}:shortest=1:'
                  f"enable='between(t,{it['start']:.3f},{it['end']:.3f})'[b{k + 1}];")
        last = f'b{k + 1}'
    chain += f'[1:v]format=yuva420p[cut];[{last}]format=yuv420p[bg];[bg][cut]overlay=0:0:shortest=1,format=yuv420p[v]'
    common.say('horneando la luz de fondo en el video (~1 min)')
    common.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(project, 'aroll.mp4'), '-c:v', 'libvpx-vp9', '-i', cut]
               + inputs + ['-filter_complex', chain, '-map', '[v]', '-map', '0:a', '-c:v', 'libx264', '-preset', 'fast',
                           '-crf', '14', '-c:a', 'copy', '-color_primaries', 'bt709', '-color_trc', 'bt709',
                           '-colorspace', 'bt709', out])
    return name


def ins_handle(c, it):
    """Small Instagram glyph + @handle, like a watermark; `spots` moves it around the frame over time."""
    handle = '@' + c.cfg.get('instagram', '').upper()
    spots = it.get('spots') or [{'t': it['start'], 'x': 830, 'y': 300}]
    for k, sp in enumerate(spots):
        s = sp['t']
        e = spots[k + 1]['t'] if k + 1 < len(spots) else it['end']
        i = c.uid('ig')
        c.add(7, f'<div id="{i}" class="clip igh" data-start="{s:.3f}" data-duration="{e - s:.3f}" '
                 f'data-track-index="7" style="left:{sp["x"]}px;top:{sp["y"]}px">'
                 f'<div class="igh-in">{IG_ICON}<span>{esc(handle)}</span></div></div>')
        c.anim(f'tl.fromTo("#{i} .igh-in",{{opacity:0}},{{opacity:0.9,duration:0.25}},{s:.3f});')


def ins_endcard(c, it):
    """Closing frame: the video darkens and the Instagram logo + handle fade in, centred."""
    i = c.uid('end')
    dur = it['end'] - it['start']
    c.add(7, f'<div id="{i}" class="clip endc" data-start="{it["start"]:.3f}" data-duration="{dur:.3f}" '
             f'data-track-index="7"><div class="endc-bg"></div><div class="endc-in">'
             f'<div class="endc-logo">{IG_ICON}</div><div class="endc-h">@{esc(c.cfg.get("instagram", "").upper())}'
             f'</div></div></div>')
    t0 = it['start']
    c.anim(f'tl.fromTo("#{i} .endc-bg",{{opacity:0}},{{opacity:1,duration:0.4,ease:"power1.out"}},{t0:.3f});')
    c.anim(f'tl.fromTo("#{i} .endc-in",{{y:30,opacity:0}},{{y:0,opacity:1,duration:0.4,ease:"power3.out"}},'
           f'{t0 + 0.2:.3f});')
    c.sfx(it.get('sfx', 'ding'), t0 + 0.2, 0.6)
def ins_title(c, it):
    i = c.uid('title')
    text = it['text']
    col = color(c.cfg, it.get('color'), c.cfg['colors']['caption'])
    fs = it.get('size') or fit_size(text, 210, ratio=0.62)
    behind = it.get('behind', False)
    y = it.get('y', SAFE['top'] + 8)   # top of the safe zone; the clip line does the 'behind' part
    font = 'hand' if it.get('font') == 'hand' else 'cal'
    letters = ''.join('<span class="tw">' + ''.join(f'<span class="l">{esc(ch)}</span>' for ch in word) + '</span>'
                      for word in text.split())
    dur = it['end'] - it['start']
    c.add(2 if behind else 6,
          f'<div id="{i}" class="clip title {font}" data-start="{it["start"]:.3f}" data-duration="{dur:.3f}" '
          f'data-track-index="{2 if behind else 6}" style="top:{y}px;color:{col};font-size:{fs}px">'
          f'<div class="title-in">{letters}</div></div>')
    if behind:
        # only the cutout below clipTop covers the title: the head hides the bottom third of the letters
        # (~80% of each letter stays visible) and lamps or shelves attached to the head in the mask never cover it
        c.clips.append((it['start'], it['end'], int(it.get('clipTop', y + fs * 0.85))))
    c.anim(f'tl.fromTo("#{i} .l",{{yPercent:110,opacity:0}},{{yPercent:0,opacity:1,duration:0.32,'
           f'ease:"back.out(2)",stagger:0.03}},{it["start"]:.3f});')
    c.anim(f'tl.fromTo("#{i} .title-in",{{scale:1}},{{scale:1.07,duration:{dur:.3f},ease:"none"}},{it["start"]:.3f});')
    c.anim(f'tl.to("#{i} .title-in",{{opacity:0,y:-30,duration:0.18}},{it["end"] - 0.18:.3f});'
           f'tl.set("#{i} .title-in",{{opacity:0}},{it["end"]:.3f});')
    c.sfx(it.get('sfx', 'whoosh'), it['start'] - 0.05)
    return behind


def ins_media(c, it, video):
    i = c.uid('media')
    src = it['src']
    mode = it.get('mode', 'full')
    dur = it['end'] - it['start']
    mw, mh = media_size(os.path.join(c.project, src))
    if mode == 'full':
        box = 'left:0;top:0;width:1080px;height:1920px'
        cls = 'full'
    else:
        w = it.get('w', 620 if mode == 'card' else 340)
        h = int(w * mh / mw)
        max_h = it.get('maxH', 560 if mode == 'card' else 500)
        if h > max_h:
            w, h = int(max_h * mw / mh), max_h
        x = it.get('x', (W - w) // 2)
        y = it.get('y', 260)
        box = f'left:{x}px;top:{y}px;width:{w}px;height:{h}px'
        cls = mode
    if video:
        el = (f'<video id="{i}v" src="{esc(src)}" data-start="{it["start"]:.3f}" data-duration="{dur:.3f}" '
              f'data-media-start="{it.get("mediaStart", 0)}" data-track-index="5" muted playsinline></video>')
        c.add(5, f'<div id="{i}" class="ins {cls}" style="{box}"><div class="frame">{el}</div></div>')
        # the wrapper is not timed (the video is), so fade it with the timeline
        c.anim(f'tl.set("#{i}",{{opacity:0}},0);tl.set("#{i}",{{opacity:1}},{it["start"]:.3f});'
               f'tl.set("#{i}",{{opacity:0}},{it["end"]:.3f});')
    else:
        c.add(5, f'<div id="{i}" class="clip ins {cls}" data-start="{it["start"]:.3f}" data-duration="{dur:.3f}" '
                 f'data-track-index="5" style="{box}"><div class="frame"><img src="{esc(src)}" alt=""></div></div>')
    rot = it.get('rot', 0 if mode == 'full' else -3)
    if mode == 'full':
        c.anim(f'tl.fromTo("#{i} .frame",{{scale:1.18,opacity:0.2}},{{scale:1,opacity:1,duration:0.28,'
               f'ease:"power3.out"}},{it["start"]:.3f});')
        c.anim(f'tl.to("#{i} .frame",{{scale:1.06,duration:{max(0.1, dur - 0.28):.3f},ease:"none"}},'
               f'{it["start"] + 0.28:.3f});')
        c.sfx(it.get('sfx', 'whoosh'), it['start'] - 0.05)
    else:
        c.anim(f'tl.fromTo("#{i} .frame",{{scale:0.3,rotation:{rot - 14},opacity:0}},{{scale:1,rotation:{rot},'
               f'opacity:1,duration:0.3,ease:"back.out(2.2)"}},{it["start"]:.3f});')
        c.anim(f'tl.to("#{i} .frame",{{y:-12,duration:{max(0.1, dur - 0.45):.3f},ease:"sine.inOut"}},'
               f'{it["start"] + 0.3:.3f});')
        c.anim(f'tl.to("#{i} .frame",{{scale:0.6,opacity:0,duration:0.15,ease:"power2.in"}},'
               f'{it["end"] - 0.15:.3f});tl.set("#{i} .frame",{{opacity:0}},{it["end"]:.3f});')
        c.sfx(it.get('sfx', 'pop'), it['start'])


def ins_scribble(c, it):
    i = c.uid('scr')
    col = color(c.cfg, it.get('color'), '#FFFFFF')
    fs = it.get('size', 170)
    dur = it['end'] - it['start']
    words = ''.join(f'<span class="sw">{esc(w)}</span>' for w in it['text'].split())
    c.add(6, f'<div id="{i}" class="clip scribble" data-start="{it["start"]:.3f}" data-duration="{dur:.3f}" '
             f'data-track-index="6" style="left:{it.get("x", 90)}px;top:{it.get("y", 400)}px;'
             f'max-width:{it.get("w", 900)}px;color:{col};font-size:{fs}px">'
             f'<div class="scr-in" style="transform:rotate({it.get("rot", -6)}deg)">{words}</div></div>')
    c.anim(f'tl.fromTo("#{i} .sw",{{clipPath:"inset(0 100% 0 0)"}},{{clipPath:"inset(0 0% 0 0)",duration:0.22,'
           f'ease:"power1.out",stagger:0.18}},{it["start"]:.3f});')
    c.sfx(it.get('sfx', 'click'), it['start'], 0.7)


def ins_profile(c, it):
    """Instagram-style follow card with the user's real name and handle (numbers come from reel.json)."""
    i = c.uid('prof')
    cfg = c.cfg
    dur = it['end'] - it['start']
    avatar = it.get('avatar', 'assets/avatar.jpg')
    has_avatar = os.path.exists(os.path.join(c.project, avatar))
    initials = ''.join(p[0] for p in cfg.get('name', 'N').split()[:2]).upper()
    av = (f'<img class="av" src="{esc(avatar)}" alt="">' if has_avatar
          else f'<div class="av av-txt">{esc(initials)}</div>')
    stats = ''
    for label, key in (('publicaciones', 'posts'), ('seguidores', 'followers'), ('seguidos', 'following')):
        if it.get(key):
            stats += f'<div class="st"><b>{esc(it[key])}</b><span>{label}</span></div>'
    name = cfg.get('name', '').split('|')[0].strip()
    bio = it.get('bio', cfg.get('name', '').split('|')[1].strip() if '|' in cfg.get('name', '') else '')
    y = it.get('y', 1000)
    c.add(9, f'<div id="{i}" class="clip prof" data-start="{it["start"]:.3f}" data-duration="{dur:.3f}" '
             f'data-track-index="9" style="top:{y}px"><div class="prof-in">'
             f'<div class="row">{av}<div class="who"><div class="handle">{esc(cfg.get("instagram", ""))}</div>'
             f'<div class="stats">{stats}</div></div></div>'
             f'<div class="nm">{esc(name)}</div><div class="bio">{esc(bio)}</div>'
             f'<div class="btn"><span class="b1">Seguir</span><span class="b2">Siguiendo</span></div>'
             f'</div><div class="cursor"></div></div>')
    t0 = it['start']
    press = t0 + min(1.1, dur * 0.45)
    c.anim(f'tl.fromTo("#{i} .prof-in",{{y:140,opacity:0,scale:0.9}},{{y:0,opacity:1,scale:1,duration:0.35,'
           f'ease:"back.out(1.8)"}},{t0:.3f});')
    c.anim(f'tl.fromTo("#{i} .cursor",{{x:260,y:260,opacity:0}},{{x:0,y:0,opacity:1,duration:0.5,'
           f'ease:"power2.out"}},{t0 + 0.35:.3f});')
    c.anim(f'tl.to("#{i} .btn",{{scale:0.92,duration:0.08}},{press:.3f});'
           f'tl.to("#{i} .btn",{{scale:1,duration:0.12}},{press + 0.08:.3f});'
           f'tl.set("#{i} .b1",{{opacity:0}},{press + 0.05:.3f});tl.set("#{i} .b2",{{opacity:1}},{press + 0.05:.3f});'
           f'tl.set("#{i} .btn",{{backgroundColor:"#EFEFEF",color:"#111"}},{press + 0.05:.3f});')
    c.anim(f'tl.to("#{i} .cursor",{{opacity:0,duration:0.2}},{press + 0.4:.3f});')
    c.anim(f'tl.to("#{i} .prof-in",{{y:60,opacity:0,duration:0.2}},{it["end"] - 0.2:.3f});'
           f'tl.set("#{i} .prof-in",{{opacity:0}},{it["end"]:.3f});')
    c.sfx('rise', t0 - 0.05, 0.8)
    c.sfx('click', press)
    c.sfx('ding', press + 0.06, 0.8)


def ins_steps(c, it):
    """A row of chips joined by arrows; each chip pops in at its own time (a process in 2-4 steps)."""
    i = c.uid('steps')
    items = it['items']
    times = it.get('times') or [it['start'] + 0.35 * k for k in range(len(items))]
    dur = it['end'] - it['start']
    acc = color(c.cfg, it.get('color'))
    parts = []
    for k, label in enumerate(items):
        if k:
            parts.append(f'<div class="arrow a{k}" style="color:{acc}">→</div>')
        hl = ' hl' if k in it.get('highlight', []) else ''
        parts.append(f'<div class="chip c{k}{hl}" style="--acc:{acc}">{esc(label)}</div>')
    title = f'<div class="steps-t" style="color:{acc}">{esc(it["title"])}</div>' if it.get('title') else ''
    c.add(6, f'<div id="{i}" class="clip steps" data-start="{it["start"]:.3f}" data-duration="{dur:.3f}" '
             f'data-track-index="6" style="top:{it.get("y", 300)}px">{title}<div class="steps-row">{"".join(parts)}'
             f'</div></div>')
    if it.get('title'):
        c.anim(f'tl.fromTo("#{i} .steps-t",{{y:30,opacity:0}},{{y:0,opacity:1,duration:0.25,ease:"back.out(2)"}},'
               f'{it["start"]:.3f});')
    for k, t in enumerate(times):
        c.anim(f'tl.fromTo("#{i} .c{k}",{{scale:0.2,opacity:0}},{{scale:1,opacity:1,'
               f'duration:0.25,ease:"back.out(2.6)"}},{t:.3f});')
        if k:
            c.anim(f'tl.fromTo("#{i} .a{k}",{{x:-30,opacity:0}},{{x:0,opacity:1,duration:0.2}},'
                   f'{t - 0.12:.3f});')
        c.sfx('pop', t, 0.8)
    c.anim(f'tl.to("#{i} .steps-row",{{opacity:0,duration:0.18}},{it["end"] - 0.18:.3f});'
           f'tl.set("#{i} .steps-row",{{opacity:0}},{it["end"]:.3f});')


def ins_webm(c, it):
    i = c.uid('wm')
    dur = it['end'] - it['start']
    w = it.get('w', 900)
    h = it.get('h', w)
    c.add(5, f'<video id="{i}" class="clip" src="{esc(it["src"])}" data-start="{it["start"]:.3f}" '
             f'data-duration="{dur:.3f}" data-track-index="5" muted playsinline style="position:absolute;'
             f'left:{it.get("x", (W - w) // 2)}px;top:{it.get("y", 260)}px;width:{w}px;height:{h}px"></video>')
    if it.get('sfx'):
        c.sfx(it['sfx'], it['start'])


# ---------------------------------------------------------------- page
CSS = """
@font-face{font-family:'Cal Sans';src:url('assets/fonts/CalSans-Regular.ttf') format('truetype')}
@font-face{font-family:'Caveat';font-weight:700;src:url('assets/fonts/Caveat-Bold.ttf') format('truetype')}
@font-face{font-family:'Inter';font-weight:600;src:url('assets/fonts/Inter-SemiBold.ttf') format('truetype')}
@font-face{font-family:'Inter';font-weight:800;src:url('assets/fonts/Inter-ExtraBold.ttf') format('truetype')}
@font-face{font-family:'Montserrat';font-weight:100 900;src:url('assets/fonts/Montserrat-Variable.ttf') format('truetype')}
@font-face{font-family:'Montserrat';font-weight:100 900;font-style:italic;
  src:url('assets/fonts/Montserrat-Italic-Variable.ttf') format('truetype')}
@font-face{font-family:'Poppins';font-weight:800;src:url('assets/fonts/Poppins-ExtraBold.ttf') format('truetype')}
@font-face{font-family:'Poppins';font-weight:800;font-style:italic;
  src:url('assets/fonts/Poppins-ExtraBoldItalic.ttf') format('truetype')}
@font-face{font-family:'Space Grotesk';font-weight:300 700;src:url('assets/fonts/SpaceGrotesk-Variable.ttf') format('truetype')}
@font-face{font-family:'Anton';src:url('assets/fonts/Anton-Regular.ttf') format('truetype')}
@font-face{font-family:'Bebas Neue';src:url('assets/fonts/BebasNeue-Regular.ttf') format('truetype')}
@font-face{font-family:'DM Serif Display';src:url('assets/fonts/DMSerifDisplay-Regular.ttf') format('truetype')}
@font-face{font-family:'DM Serif Display';font-style:italic;
  src:url('assets/fonts/DMSerifDisplay-Italic.ttf') format('truetype')}
html,body{margin:0;background:#000;overflow:hidden}
#root{position:relative;width:100%;height:100%;overflow:hidden;background:#000;font-family:'Inter',sans-serif}
#stage{position:absolute;inset:0;transform-origin:50% 35%}
#stage video{position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover}
.layer{position:absolute;inset:0;pointer-events:none}
.cap{position:absolute;left:SL;right:SR;display:flex;justify-content:center}
.cap-in{display:flex;flex-wrap:wrap;justify-content:center;align-items:baseline;gap:0 22px;text-align:center}
.num{position:absolute;right:0;display:flex;justify-content:center;font-family:'Inter',sans-serif;
  font-weight:800;line-height:1;color:transparent;filter:drop-shadow(0 6px 20px rgba(0,0,0,.25))}
.anim{position:absolute;display:flex;flex-direction:column;align-items:center;gap:10px}
.anim-in{width:100%;aspect-ratio:1;filter:drop-shadow(0 4px 14px rgba(0,0,0,.4))}
.anim.badge .anim-in{background:#fff;border-radius:28%;padding:14%;box-sizing:border-box;
  filter:drop-shadow(0 14px 30px rgba(0,0,0,.35))}
.anim svg{width:100%;height:100%;overflow:visible;fill:none;stroke:var(--fg);stroke-width:5.5;
  stroke-linecap:round;stroke-linejoin:round}
.anim svg [pathLength]{stroke-dasharray:1;stroke-dashoffset:0}
.anim svg .k{stroke:var(--acc)}
.anim svg .p{fill:var(--fg);stroke:none}
.anim-l{font-family:'Inter',sans-serif;font-weight:800;font-size:44px;color:#fff;white-space:nowrap;
  text-shadow:0 3px 14px rgba(0,0,0,.45)}
.igh{position:absolute}
.igh-in{display:flex;flex-direction:column;align-items:flex-start;gap:10px;color:#fff;
  filter:drop-shadow(0 2px 6px rgba(0,0,0,.4))}
.igh-in svg{width:46px;height:46px}
.igh-in span{font-family:'Inter',sans-serif;font-weight:800;font-size:20px;letter-spacing:0.5px}
.endc{position:absolute;inset:0}
.endc-bg{position:absolute;inset:0;background:rgba(12,12,12,.72)}
.endc-in{position:absolute;left:0;right:0;top:760px;display:flex;flex-direction:column;align-items:center;
  gap:26px;color:#fff}
.endc-logo svg{width:150px;height:150px}
.endc-h{font-family:'Inter',sans-serif;font-weight:800;font-size:40px;letter-spacing:1px}
.title{position:absolute;left:30px;right:30px;display:flex;justify-content:center;text-align:center}
.title.cal{font-family:TITLEF;line-height:0.92;text-shadow:0 10px 30px rgba(0,0,0,.25)}
.title.hand{font-family:'Caveat',cursive;font-weight:700;line-height:0.9}
.title-in{display:flex;flex-wrap:wrap;justify-content:center;gap:0 0.25em;padding:0.08em 0}
.tw{display:inline-flex;white-space:nowrap;overflow:hidden;padding:0.06em 0.02em}
.l{display:inline-block}
.ins{position:absolute}
.ins .frame{position:absolute;inset:0;overflow:hidden}
.ins.card .frame{border:10px solid #fff;border-radius:30px;box-shadow:0 24px 60px rgba(0,0,0,.45)}
.ins.sticker .frame{overflow:visible;filter:drop-shadow(0 16px 24px rgba(0,0,0,.45))}
.ins img,.ins video{width:100%;height:100%;object-fit:cover;display:block}
.ins.sticker img{object-fit:contain}
.scribble{position:absolute;font-family:'Caveat',cursive;font-weight:700;line-height:0.95;
  text-shadow:OUTLINE}
.scr-in{display:flex;flex-wrap:wrap;gap:0 0.25em}
.sw{display:inline-block}
.prof{position:absolute;left:70px;right:110px}
.prof-in{background:#fff;border-radius:36px;padding:34px 38px;box-shadow:0 30px 80px rgba(0,0,0,.45);color:#111}
.prof .row{display:flex;align-items:center;gap:30px}
.prof .av{width:180px;height:180px;border-radius:50%;object-fit:cover;flex:none;
  box-shadow:0 0 0 6px #fff,0 0 0 11px ACC0}
.prof .av-txt{display:flex;align-items:center;justify-content:center;background:CAPC;color:#111;
  font-family:'Cal Sans',sans-serif;font-size:76px}
.prof .handle{font-weight:800;font-size:54px;margin-bottom:12px}
.prof .stats{display:flex;gap:28px}
.prof .st{display:flex;flex-direction:column;font-size:28px;color:#555}
.prof .st b{font-size:40px;color:#111;font-weight:800}
.prof .nm{font-weight:800;font-size:40px;margin-top:22px}
.prof .bio{font-size:34px;color:#444;margin-top:4px}
.prof .btn{position:relative;margin-top:24px;height:92px;border-radius:20px;background:#0095F6;color:#fff;
  font-weight:800;font-size:40px;display:flex;align-items:center;justify-content:center}
.prof .btn span{position:absolute}
.prof .b2{opacity:0}
.prof .cursor{position:absolute;right:170px;bottom:30px;width:64px;height:64px;border-radius:50%;
  background:rgba(255,255,255,.85);box-shadow:0 0 0 4px rgba(0,0,0,.25)}
.steps{position:absolute;left:40px;right:40px;display:flex;flex-direction:column;align-items:center;gap:18px}
.steps-t{font-family:'Cal Sans',sans-serif;font-size:96px;text-shadow:OUTLINE}
.steps-row{display:flex;align-items:center;justify-content:center;gap:14px}
.chip{display:block;background:#fff;color:#141414;font-family:'Cal Sans',sans-serif;font-size:58px;
  padding:22px 30px;border-radius:26px;box-shadow:0 14px 34px rgba(0,0,0,.35);white-space:nowrap}
.chip.hl{background:var(--acc);color:#141414}
.arrow{display:block;font-family:'Inter',sans-serif;font-weight:800;font-size:60px;text-shadow:OUTLINE}
#flash{position:absolute;inset:0;background:#fff;opacity:0}
.safe{position:absolute;border:3px solid rgba(255,0,0,.9);pointer-events:none}
"""


def shadow():
    """Soft drop shadow for text on video. No outline: a shadow reads cleaner on video."""
    return '0 4px 14px rgba(0,0,0,.55),0 2px 4px rgba(0,0,0,.45)'


def main():
    if len(sys.argv) < 2:
        common.die('uso: build.py <project> [--safe]')
    safe = '--safe' in sys.argv
    cfg = common.load_config()
    project = common.project_dir(sys.argv[1])
    segments = common.read_json(os.path.join(project, 'segments.json'))
    caps = common.read_json(os.path.join(project, 'captions.json'), [])
    reel = common.read_json(os.path.join(project, 'reel.json'), {})
    cfg['_sfx_gain'] = float(reel.get('sfx', {}).get('gain', 1.0))
    cfg['_emph'] = reel.get('captions', {}).get('emphColor')   # icons take the emphasis colour as their accent
    total = segments[-1]['end_frame'] / common.FPS

    # shared assets into the project (fonts, sfx, gsap)
    if os.path.isdir(MATTER_DIR):
        os.makedirs(os.path.join(project, 'assets', 'brand'), exist_ok=True)
        for f in glob.glob(os.path.join(MATTER_DIR, 'Matter-*.otf')):
            shutil.copy(f, os.path.join(project, 'assets', 'brand'))
    for sub in ('fonts', 'sfx', 'vendor'):
        src = os.path.join(common.SKILL_DIR, 'assets', sub)
        dst = os.path.join(project, 'assets', sub)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
    if not os.path.exists(os.path.join(project, 'assets', 'vendor', 'gsap.min.js')):
        common.die('falta assets/vendor/gsap.min.js: correr scripts/setup.py')

    c = Comp(cfg, project, safe)
    cap_style = caption_style(reel.get('captions', {}), cfg)
    build_captions(c, caps, cap_style)

    needs_cutout = False
    for it in sorted(reel.get('inserts', []), key=lambda x: x['start']):
        t = it['type']
        if t == 'title':
            needs_cutout |= ins_title(c, it)
        elif t == 'broll':
            ins_media(c, it, video=True)
        elif t == 'image':
            ins_media(c, it, video=False)
        elif t == 'scribble':
            ins_scribble(c, it)
        elif t == 'profile':
            ins_profile(c, it)
        elif t == 'steps':
            ins_steps(c, it)
        elif t == 'webm':
            ins_webm(c, it)
        elif t == 'number':
            ins_number(c, it)
        elif t == 'anim':
            ins_anim(c, it)
        elif t == 'scene':
            ins_scene(c, it)
        elif t == 'light':
            pass   # baked into the a-roll below (lit_aroll)
        elif t == 'handle':
            ins_handle(c, it)
        elif t == 'endcard':
            ins_endcard(c, it)
        else:
            common.die(f'tipo de insert desconocido: {t}')
    cut_path = os.path.join(project, 'assets', 'cutout.webm')
    if needs_cutout and not os.path.exists(cut_path):
        common.die('hay títulos "behind" o luces de fondo pero falta assets/cutout.webm: correr cutout.py primero')

    # camera moves: explicit zooms + a quick punch on every emphasis caption
    zooms = list(reel.get('zooms', []))
    if reel.get('autoZoom', True):
        for g in caps:
            if g.get('emph'):
                zooms.append({'start': g['start'], 'end': g['end'], 'scale': 1.08, 'fast': True})
    for z in sorted(zooms, key=lambda z: z['start']):
        s, e, k = z['start'], z['end'], z.get('scale', 1.15)
        ox, oy = z.get('ox', 0.5), z.get('oy', 0.35)
        c.anim(f'tl.set("#stage",{{transformOrigin:"{ox * 100:.0f}% {oy * 100:.0f}%"}},{s:.3f});')
        c.anim(f'tl.to("#stage",{{scale:{k},duration:{0.12 if z.get("fast") else 0.35},ease:"power3.out"}},{s:.3f});')
        c.anim(f'tl.to("#stage",{{scale:1,duration:0.2,ease:"power2.inOut"}},{max(s + 0.15, e - 0.2):.3f});')
    if reel.get('flashes'):
        c.anim('tl.set("#flash",{opacity:0},0);')
    for f in reel.get('flashes', []):
        c.anim(f'tl.fromTo("#flash",{{opacity:0.85}},{{opacity:0,duration:0.22,ease:"power2.out",'
               f'immediateRender:false}},{f:.3f});')
        c.sfx('whoosh', f - 0.05, 0.8)

    music = reel.get('music')
    if music:
        vol = music.get('volume', 0.08)
        fade = f'{{"version":1,"lanes":[{{"target":"volume","points":[{{"t":0,"v":{vol}}},' \
               f'{{"t":{total - 1.2:.2f},"v":{vol}}},{{"t":{total:.2f},"v":0}}]}}]}}'
        c.audio.append(f'<audio id="music" src="{esc(music["src"])}" data-start="0" data-duration="{total:.3f}" '
                       f'data-track-index="30" data-volume="{vol}" data-automation=\'{fade}\'></audio>')

    col = cfg['colors']
    tf = FONTS.get(reel.get('titleFont', 'cal')) or common.die(f'titleFont: hay {", ".join(FONTS)}')
    css = ((CSS + caption_css(cap_style) + scenes.CSS).replace('CAPC', col['caption']).replace('OUTLINE', shadow())
           .replace('TITLEF', f"{tf['family']},sans-serif;font-weight:{tf['weight']}")
           .replace('ACC0', col['accents'][0]).replace('SL', f'{SAFE["left"]}px')
           .replace('SR', f'{W - SAFE["right_low"]}px'))
    lights = [it for it in reel.get('inserts', []) if it['type'] == 'light']
    aroll_src = lit_aroll(project, cfg, lights) if lights else 'aroll.mp4'
    stage = [f'<video id="aroll" class="clip" src="{aroll_src}" data-start="0" data-duration="{total:.3f}" '
             f'data-track-index="0" playsinline data-has-audio="true"></video>']
    stage.append('<div class="layer" id="behind">' + ''.join(c.layers.pop(2, [])) + '</div>')
    if needs_cutout:
        stage.append(f'<video id="cutout" class="clip" src="{clipped_cutout(project, c.clips)}" data-start="0" '
                     f'data-duration="{total:.3f}" data-track-index="1" muted playsinline></video>')
    layers = ''.join(f'<div class="layer" id="z{z}">' + ''.join(v) + '</div>' for z, v in sorted(c.layers.items()))
    guide = ''
    if safe:
        guide = (f'<div class="safe" style="left:{SAFE["left"]}px;top:{SAFE["top"]}px;'
                 f'width:{SAFE["right"] - SAFE["left"]}px;height:{SAFE["bottom"] - SAFE["top"]}px"></div>'
                 f'<div class="safe" style="left:{SAFE["right_low"]}px;top:{SAFE["right_low_from"]}px;width:0;'
                 f'height:{SAFE["bottom"] - SAFE["right_low_from"]}px"></div>')
    page = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width={W}, height={H}">
<title>reel</title>
<script src="assets/vendor/gsap.min.js"></script>
<style>{css}</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-width="{W}" data-height="{H}" data-duration="{total:.3f}">
<div id="stage">{''.join(stage)}</div>
{layers}
<div id="flash"></div>
{guide}
{''.join(c.audio)}
</div>
<script>
document.fonts.ready.then(function () {{
  const tl = gsap.timeline({{ paused: true }});
  {chr(10).join('  ' + a for a in c.tl)}
  window.__timelines["main"] = tl;
}});
</script>
</body>
</html>
"""
    with open(os.path.join(project, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page)
    for name in ('hyperframes.json',):
        p = os.path.join(project, name)
        if not os.path.exists(p):
            common.write_json(p, {'name': os.path.basename(project)})
    common.say(f'OK index.html  {common.tc(total)}  {len(caps)} subtítulos, '
               f'{len(reel.get("inserts", []))} inserts, {len(c.audio)} sonidos'
               + ('  [guía de zona segura]' if safe else ''))


if __name__ == '__main__':
    main()
