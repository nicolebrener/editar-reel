"""Paso 5: turns words.json into caption groups (captions.json) that build.py animates.

    PY scripts/captions.py <project> [--emph "zapia,gratis,whatsapp"] [--fix "sapia=Zapia;cloud=Claude"]
                                     [--max-words 3] [--force]

Rules (from the reference reels):
  - 1 to 3 words on screen at a time, no full stops or commas, ? and ! stay.
  - A new group starts at punctuation, at a pause over 0.3 s, and at every cut.
  - Emphasis words (--emph) always stand alone: bigger, in an accent colour, with a pop.
    Accent colours rotate through config colors.accents.

captions.json is meant to be edited by hand (or by Claude) after this: fix a word, move an emphasis,
change "y" for one group. The file is not overwritten unless you pass --force.

    [{"id": "k1", "start": 0.12, "end": 0.71, "y": null,
      "words": [{"t": "Esto", "s": 0.12, "e": 0.30}, {"t": "cambia", "s": 0.31, "e": 0.70}],
      "emph": null},
     {"id": "k2", ..., "words": [{"t": "TODO", ...}], "emph": {"color": 0}}]
"""
import argparse
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

BREAK_AFTER = re.compile(r'[.,;:?!…]$')
WEAK = {'y', 'e', 'o', 'u', 'a', 'de', 'del', 'al', 'la', 'el', 'lo', 'los', 'las', 'un', 'una', 'me', 'te', 'se',
        'le', 'les', 'nos', 'mi', 'tu', 'su', 'que', 'con', 'por', 'para', 'en', 'si', 'ni', 'es', 'muy', 'mas'}


def norm(s):
    s = unicodedata.normalize('NFD', s.lower())
    return re.sub(r'[^a-z0-9ñ]', '', ''.join(c for c in s if unicodedata.category(c) != 'Mn'))


def clean(t):
    t = t.strip().strip('"“”«»')
    # captions carry no punctuation (as in the reference reels): ¿? and ¡! come out in pairs or not at all
    return re.sub(r'[.,;:…?!]+$', '', t).lstrip('¿¡')


def apply_fixes(words, fixes):
    """"sapia=Zapia;una agente=un agente": the left side can be several words; the right side
    must have the same number of words (each keeps its timing)."""
    for pair in filter(None, (fixes or '').split(';')):
        if '=' not in pair:
            continue
        a, b = pair.split('=', 1)
        src, dst = [norm(t) for t in a.split()], b.split()
        if len(dst) != len(src):
            if len(src) == 1:
                dst = [b.strip()]          # one word becomes a short phrase: "míros=me los"
            else:
                common.die(f'--fix "{pair}": los dos lados tienen que tener la misma cantidad de palabras')
        for i in range(len(words) - len(src) + 1):
            if all(norm(words[i + k]['w']) == src[k] for k in range(len(src))):
                for k in range(len(src)):
                    tail = re.findall(r'[.,;:?!…]+$', words[i + k]['w'])
                    words[i + k]['w'] = dst[k] + (tail[0] if tail else '')
    return words


def mark_emphasis(words, phrases):
    """Marks words that match an emphasis phrase; returns {word index: phrase number}."""
    marks = {}
    for pn, phrase in enumerate(phrases):
        toks = [norm(t) for t in phrase.split() if norm(t)]
        for i in range(len(words) - len(toks) + 1):
            if toks and all(norm(words[i + k]['w']) == toks[k] for k in range(len(toks))):
                for k in range(len(toks)):
                    marks.setdefault(i + k, (pn, i))
    return marks


def group(words, phrases, max_words, max_chars=18, gap=0.3):
    groups, cur = [], []
    marks = mark_emphasis(words, phrases)

    def flush():
        if cur:
            groups.append(list(cur))
            cur.clear()

    for i, w in enumerate(words):
        prev = words[i - 1] if i else None
        if prev is not None and (w['s'] - prev['e'] > gap or w.get('seg') != prev.get('seg')):
            flush()
        if i in marks:
            if not (cur and cur[-1].get('emph') == marks[i]):
                flush()
            cur.append(dict(w, emph=marks[i]))
            if i + 1 not in marks or marks[i + 1] != marks[i]:
                flush()
            continue
        if cur and cur[-1].get('emph'):
            flush()
        text_len = sum(len(x['w']) + 1 for x in cur) + len(w['w'])
        if len(cur) >= max_words or (cur and text_len > max_chars):
            # never end a group on "y", "la", "me"...: carry those words to the next group
            carry = []
            while len(cur) > 1 and norm(cur[-1]['w']) in WEAK and not BREAK_AFTER.search(cur[-1]['w']):
                carry.insert(0, cur.pop())
            flush()
            cur.extend(carry)
        cur.append(w)
        if BREAK_AFTER.search(w['w']):
            flush()
    flush()

    # a lone weak word ("con" right before an emphasis) joins the group before it when that one has room
    merged = []
    for g in groups:
        lone = len(g) == 1 and not g[0].get('emph') and norm(g[0]['w']) in WEAK
        prev = merged[-1] if merged else None
        if lone and prev and not prev[0].get('emph') and len(prev) < max_words + 1 \
                and g[0]['s'] - prev[-1]['e'] < 0.4:
            prev.append(g[0])
        else:
            merged.append(g)
    groups = merged

    out, color = [], 0
    for n, g in enumerate(groups):
        nxt = groups[n + 1][0]['s'] if n + 1 < len(groups) else g[-1]['e'] + 0.4
        end = min(nxt, g[-1]['e'] + 0.45)
        item = {'id': f'k{n + 1}', 'start': round(g[0]['s'], 3), 'end': round(max(end, g[0]['s'] + 0.25), 3),
                'y': None, 'words': [{'t': clean(w['w']), 's': w['s'], 'e': w['e']} for w in g], 'emph': None}
        item['words'] = [w for w in item['words'] if w['t']]
        if not item['words']:
            continue
        if g[0].get('emph'):
            item['emph'] = {'color': color}
            color += 1
        out.append(item)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--emph', default='', help='palabras a destacar, separadas por coma')
    ap.add_argument('--fix', default='', help='correcciones: "sapia=Zapia;cloud=Claude"')
    ap.add_argument('--max-words', type=int, default=3)
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()

    project = common.project_dir(a.project)
    out = os.path.join(project, 'captions.json')
    if os.path.exists(out) and not a.force:
        common.die('captions.json ya existe (editalo, o pasá --force para regenerarlo)')
    words = apply_fixes(common.read_json(os.path.join(project, 'words.json')), a.fix)
    phrases = [x.strip() for x in a.emph.split(',') if x.strip()]
    caps = group(words, phrases, a.max_words)
    common.write_json(out, caps)
    common.say(f'OK {len(caps)} grupos de subtítulos, {sum(1 for c in caps if c["emph"])} destacados')
    for c in caps:
        txt = ' '.join(w['t'] for w in c['words'])
        common.say(f'  {c["id"]:>4} {c["start"]:6.2f}  {"*" + txt.upper() + "*" if c["emph"] else txt}')


if __name__ == '__main__':
    main()
