"""Paso 2: registers the raw clips, makes contact sheets and transcribes every take.

    PY scripts/ingest.py <project> <clips or folder> [--newest N] [--prompt "nombres, marcas"]

Writes:
    clips.json            c1, c2, ... -> original file + size, duration, HDR flag
    work/sheets.jpg       one row per clip, 5 frames each (to see setups and angles)
    work/words_cN.json    word-level transcript of each clip
    transcript.txt        what was said in every clip, by line, with times and pauses

Originals are only read. Re-running skips clips that are already transcribed.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

VIDEO_EXT = ('.mov', '.mp4', '.m4v', '.mkv', '.webm')


def find_clips(inputs, newest):
    files = []
    for p in inputs:
        p = common.expand(p)
        if os.path.isdir(p):
            files += [os.path.join(p, f) for f in os.listdir(p)
                      if f.lower().endswith(VIDEO_EXT) and not f.startswith('.')]
        elif os.path.isfile(p):
            files.append(p)
        else:
            common.die(f'no existe: {p}')
    files = sorted(set(files), key=os.path.getmtime)
    if newest:
        files = files[-newest:]
    return files


def contact_sheets(project, clips):
    from PIL import Image, ImageDraw, ImageFont
    tw, th, n = 150, 266, 5
    sheet = Image.new('RGB', (110 + n * (tw + 6), len(clips) * (th + 8) + 8), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(os.path.join(common.SKILL_DIR, 'assets', 'fonts', 'Inter-SemiBold.ttf'), 22)
    except OSError:
        font = ImageFont.load_default()
    tmp = os.path.join(project, 'work', '_thumb.jpg')
    for row, (cid, c) in enumerate(clips.items()):
        y = 8 + row * (th + 8)
        draw.text((10, y + 8), cid, fill=(255, 214, 10), font=font)
        draw.text((10, y + 40), common.tc(c['duration']), fill=(200, 200, 200), font=font)
        for i in range(n):
            t = c['duration'] * (i + 0.5) / n
            common.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.2f}', '-i', c['path'], '-frames:v', '1',
                        '-vf', f'scale={tw}:{th}:force_original_aspect_ratio=decrease,pad={tw}:{th}:-1:-1', tmp])
            sheet.paste(Image.open(tmp).convert('RGB'), (110 + i * (tw + 6), y))
    out = os.path.join(project, 'work', 'sheets.jpg')
    sheet.save(out, quality=85)
    os.remove(tmp)
    return out


def load_model(cfg, model_name=None):
    from faster_whisper import WhisperModel
    name = model_name or cfg.get('whisperModel', 'small')
    common.say(f'cargando whisper {name} (la primera vez lo descarga)')
    return WhisperModel(name, device='cpu', compute_type='int8')


def transcribe(model, media, work, prompt, language):
    """Word-level transcript of one file. Returns [{'w','s','e'}] in the file's own time."""
    import numpy as np
    # decode with ffmpeg ourselves: faster-whisper's own decoder breaks with some PyAV versions
    raw = common.run(['ffmpeg', '-v', 'error', '-i', media, '-vn', '-ac', '1', '-ar', '16000',
                      '-f', 's16le', '-'], capture_bytes=True).stdout
    audio = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    segments, _ = model.transcribe(audio, language=language, word_timestamps=True, beam_size=5,
                                   condition_on_previous_text=False, initial_prompt=prompt or None,
                                   vad_filter=False)
    words = []
    for seg in segments:
        for w in seg.words or []:
            words.append({'w': w.word.strip(), 's': round(w.start, 3), 'e': round(w.end, 3),
                          'p': round(w.probability, 2)})
    return [w for w in words if w['w']]


def lines_from_words(words, gap=0.6):
    """Groups words into lines wherever the speaker pauses longer than `gap` seconds."""
    lines, cur = [], []
    for w in words:
        if cur and w['s'] - cur[-1]['e'] > gap:
            lines.append(cur)
            cur = []
        cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('inputs', nargs='*')
    ap.add_argument('--newest', type=int, default=0)
    ap.add_argument('--prompt', default='', help='nombres y palabras clave para que Whisper las escriba bien')
    ap.add_argument('--model', default=None)
    a = ap.parse_args()

    cfg = common.load_config()
    project = common.project_dir(a.project)
    work = os.path.join(project, 'work')
    clips_path = os.path.join(project, 'clips.json')
    clips = common.read_json(clips_path, {})

    inputs = a.inputs or [cfg['clipsDir']]
    known = {c['path']: cid for cid, c in clips.items()}
    for f in find_clips(inputs, a.newest):
        if f in known:
            continue
        cid = f'c{len(clips) + 1}'
        info = common.video_info(f)
        clips[cid] = {k: info[k] for k in ('path', 'width', 'height', 'duration', 'fps', 'hdr', 'has_audio')}
        clips[cid]['file'] = os.path.basename(f)
    if not clips:
        common.die('no encontré clips de video')
    common.write_json(clips_path, clips)
    common.say(f'{len(clips)} clips registrados')
    if a.prompt:   # assemble.py reuses it when it transcribes the final cut
        with open(os.path.join(work, 'prompt.txt'), 'w', encoding='utf-8') as f:
            f.write(a.prompt)

    common.say('hoja de contactos: ' + contact_sheets(project, clips))

    model = None
    out = []
    for cid, c in clips.items():
        wpath = os.path.join(work, f'words_{cid}.json')
        if not os.path.exists(wpath):
            if not c['has_audio']:
                common.write_json(wpath, [])
            else:
                model = model or load_model(cfg, a.model)
                common.say(f'transcribiendo {cid} {c["file"]} ({common.tc(c["duration"])})')
                common.write_json(wpath, transcribe(model, c['path'], work, a.prompt, cfg.get('language', 'es')))
        words = common.read_json(wpath)
        head = (f'== {cid}  {c["file"]}  {common.tc(c["duration"])}  {c["width"]}x{c["height"]}'
                f'{"  HDR" if c["hdr"] else ""}')
        out.append(head)
        if not words:
            out.append('  (sin voz: b-roll o grabación de pantalla)')
        lines = lines_from_words(words)
        for ln in lines:
            low = [w['w'] for w in ln if w['p'] < 0.5]
            txt = ' '.join(w['w'] for w in ln)
            out.append(f'  [{ln[0]["s"]:6.2f} - {ln[-1]["e"]:6.2f}] {txt}'
                       + (f'   (dudosas: {", ".join(low)})' if low else ''))
        pauses = [f'{a_[-1]["e"]:.2f}-{b_[0]["s"]:.2f}' for a_, b_ in zip(lines, lines[1:])]
        if pauses:
            out.append('  pausas: ' + ', '.join(pauses))
        out.append('')
    with open(os.path.join(project, 'transcript.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    common.say('transcript: ' + os.path.join(project, 'transcript.txt'))


if __name__ == '__main__':
    main()
