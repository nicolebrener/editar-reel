"""Paso 4: cuts the segments in edl.json from the originals and joins them into aroll.mp4.

    PY scripts/assemble.py <project>

edl.json is a list of segments, in order:
    [{"id": "gancho", "clip": "c3", "in": 12.66, "out": 15.72, "zoom": 1.0, "cx": 0.5, "cy": 0.45,
      "line": "lo que dice"}]
    zoom 1.0 = full frame; 1.3-1.8 = punch-in (cut from the 4K original, so it stays sharp)
    cx / cy  = centre of the crop, 0-1 of the frame (0.5, 0.42 keeps the face centred)

Writes:
    aroll.mp4        1080x1920, 30 fps constant, SDR Rec.709, loudness -14 LUFS
    segments.json    every segment with its exact start/end frame on the final timeline
    words.json       the words of every segment, moved to timeline time (for captions)
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

FPS, W, H = common.FPS, common.W, common.H


def crop_box(cw_src, ch_src, zoom, cx, cy):
    """Crop rectangle (w, h, x, y) for a 9:16 frame at `zoom`, centred on (cx, cy)."""
    if cw_src / ch_src > 9 / 16:
        cw, ch = ch_src * 9 / 16, ch_src
    else:
        cw, ch = cw_src, cw_src * 16 / 9
    cw, ch = cw / zoom, ch / zoom
    x = min(max(cx * cw_src - cw / 2, 0), cw_src - cw)
    y = min(max(cy * ch_src - ch / 2, 0), ch_src - ch)
    ev = lambda v: int(v) // 2 * 2  # noqa: E731
    return ev(cw), ev(ch), ev(x), ev(y)


def video_chain(info, seg, exposure):
    w, h, x, y = crop_box(info['width'], info['height'], float(seg.get('zoom', 1.0)),
                          float(seg.get('cx', 0.5)), float(seg.get('cy', 0.5)))
    chain = f'crop={w}:{h}:{x}:{y},'
    if info['hdr']:
        lut = common.hdr_lut_path(exposure).replace('\\', '/').replace(':', '\\:')
        chain += (f'scale={W}:{H}:flags=lanczos:in_color_matrix=bt2020:in_range=tv,format=gbrp16le,'
                  f"lut3d='{lut}',scale=out_color_matrix=bt709:out_range=tv,")
    else:
        chain += f'scale={W}:{H}:flags=lanczos,'
    # tag the frames as SDR Rec.709: otherwise they keep the iPhone's HLG tags and the renderer treats
    # the whole reel as HDR (washed-out colours, slow layered render)
    return chain + f'setsar=1,fps={FPS},format=yuv420p,' \
                   'setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv'


def render_segment(project, clips, seg, idx, exposure):
    clip = clips.get(seg['clip']) or common.die(f'el segmento {seg.get("id")} usa {seg["clip"]}, que no existe')
    n = round((seg['out'] - seg['in']) * FPS)
    if n <= 0:
        common.die(f'segmento {seg.get("id")}: out tiene que ser mayor que in')
    dur = n / FPS
    key = json.dumps(['v2', clip['path'], seg['in'], n, seg.get('zoom', 1), seg.get('cx', .5), seg.get('cy', .5),
                      exposure], sort_keys=True)
    out = os.path.join(project, 'work', 'segs', f'{idx:02d}_{hashlib.md5(key.encode()).hexdigest()[:8]}.mp4')
    if os.path.exists(out):
        return out, n
    os.makedirs(os.path.dirname(out), exist_ok=True)
    vf = video_chain(clip, seg, exposure) + f',trim=end_frame={n},setpts=PTS-STARTPTS'
    cmd = ['ffmpeg', '-v', 'error', '-y', '-ss', f'{seg["in"]:.3f}', '-t', f'{dur + 0.5:.3f}', '-i', clip['path']]
    if clip['has_audio']:
        af = f'aresample=48000,atrim=end={dur:.4f},asetpts=PTS-STARTPTS,apad=whole_dur={dur:.4f}'
        cmd += ['-filter_complex', f'[0:v]{vf}[v];[0:a]{af}[a]', '-map', '[v]', '-map', '[a]']
    else:
        cmd += ['-f', 'lavfi', '-t', f'{dur:.4f}', '-i', 'anullsrc=r=48000:cl=stereo',
                '-filter_complex', f'[0:v]{vf}[v]', '-map', '[v]', '-map', '1:a']
    cmd += ['-c:v', 'libx264', '-preset', 'fast', '-crf', '14', '-c:a', 'pcm_s16le', '-ac', '2',
            '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
            out.replace('.mp4', '.mkv')]
    common.run(cmd)
    os.replace(out.replace('.mp4', '.mkv'), out)
    return out, n


def main():
    if len(sys.argv) < 2:
        common.die('uso: assemble.py <project>')
    cfg = common.load_config()
    project = common.project_dir(sys.argv[1])
    clips = common.read_json(os.path.join(project, 'clips.json'))
    edl = common.read_json(os.path.join(project, 'edl.json'))
    exposure = float(cfg.get('hdrExposure', 0.62))

    parts, segments, frame = [], [], 0
    for i, seg in enumerate(edl):
        common.say(f'segmento {i + 1}/{len(edl)} {seg.get("id", "")}')
        path, n = render_segment(project, clips, seg, i, exposure)
        parts.append(path)
        segments.append(dict(seg, start_frame=frame, end_frame=frame + n,
                             start=round(frame / FPS, 4), end=round((frame + n) / FPS, 4)))
        frame += n

    # join: one concat filter, then gentle cleanup + loudness for the voice
    cmd = ['ffmpeg', '-v', 'error', '-y']
    for p in parts:
        cmd += ['-i', p]
    streams = ''.join(f'[{i}:v][{i}:a]' for i in range(len(parts)))
    fc = (f'{streams}concat=n={len(parts)}:v=1:a=1[v][a0];'
          '[a0]highpass=f=70,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]')
    out = os.path.join(project, 'aroll.mp4')
    cmd += ['-filter_complex', fc, '-map', '[v]', '-map', '[a]', '-r', str(FPS),
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p',
            '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
            '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out]
    common.run(cmd)
    common.write_json(os.path.join(project, 'segments.json'), segments)

    # words on the timeline: transcribe the finished cut itself, so a cut inside a word or a
    # removed stumble can never shift the captions
    import ingest
    prompt_path = os.path.join(project, 'work', 'prompt.txt')
    prompt = open(prompt_path, encoding='utf-8').read() if os.path.exists(prompt_path) else ''
    common.say('transcribiendo el corte final (whisper medium)')
    model = ingest.load_model(cfg, cfg.get('whisperModelFinal', 'medium'))
    words = ingest.transcribe(model, out, os.path.join(project, 'work'), prompt, cfg.get('language', 'es'))
    for w in words:
        w['seg'] = next((s.get('id') for s in segments if s['start'] <= w['s'] < s['end']), segments[-1].get('id'))
    common.write_json(os.path.join(project, 'words.json'), words)

    info = common.video_info(out)
    common.say(f'OK aroll.mp4 {common.tc(info["duration"])} ({frame} frames), {len(segments)} segmentos, '
               f'{len(words)} palabras')


if __name__ == '__main__':
    main()
