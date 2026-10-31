"""Paso 7: checks a finished render and makes the phone copy.

    PY scripts/check.py <project> renders/<name>.mp4

Writes, next to the render:
    work/cut_check.jpg     for every cut: the last frame before it and the first frame after it.
                           Every "after" frame must show the new shot cleanly (no leftover frame, no black).
    <name>-celu.mp4        1080x1920 copy to send to the phone (the render itself stays 4K)
Prints the loudness and peak of the audio (peak should sit around -1 to -3 dB, never 0).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


def main():
    if len(sys.argv) < 3:
        common.die('uso: check.py <project> renders/<archivo>.mp4')
    project = common.project_dir(sys.argv[1])
    render = sys.argv[2] if os.path.isabs(sys.argv[2]) else os.path.join(project, sys.argv[2])
    segments = common.read_json(os.path.join(project, 'segments.json'))
    info = common.video_info(render)
    expected = segments[-1]['end_frame'] / common.FPS
    common.say(f'render: {info["width"]}x{info["height"]} {info["fps"]} fps, {info["duration"]:.2f} s '
               f'(esperado {expected:.2f} s)')
    if (info['width'], info['height']) != (common.VW, common.VH):
        common.say(f'ATENCION: el render no es 4K ({common.VW}x{common.VH}): falta --resolution portrait-4k')
    if abs(info['duration'] - expected) > 0.15:
        common.say('ATENCION: la duración no coincide con segments.json')

    # frames around every cut, straight from the render
    frames = []
    for s in segments[1:]:
        frames += [s['start_frame'] - 1, s['start_frame']]
    if frames:
        sel = '+'.join(f'eq(n\\,{f})' for f in frames)
        cols = 6
        rows = (len(frames) + cols - 1) // cols
        out = os.path.join(project, 'work', 'cut_check.jpg')
        common.run(['ffmpeg', '-v', 'error', '-y', '-i', render, '-vf',
                    f"select='{sel}',scale=180:-2,tile={cols}x{rows}:padding=4:color=white",
                    '-frames:v', '1', '-fps_mode', 'passthrough', out])
        common.say(f'cortes: {out}  (pares antes|después, {len(segments) - 1} cortes)')

    r = common.run(['ffmpeg', '-hide_banner', '-nostats', '-i', render, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                   capture=True, check=False)
    lufs = re.findall(r'I:\s+(-?[\d.]+) LUFS', r.stderr)
    peak = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', r.stderr)
    if lufs:
        common.say(f'audio: {lufs[-1]} LUFS integrado, pico {peak[-1] if peak else "?"} dBFS'
                   + ('  ATENCION: clipea' if peak and float(peak[-1]) > -0.5 else ''))

    phone = os.path.splitext(render)[0] + '-celu.mp4'
    common.run(['ffmpeg', '-v', 'error', '-y', '-i', render, '-vf', f'scale={common.W}:{common.H}:flags=lanczos',
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-c:a', 'aac', '-b:a', '160k',
                '-movflags', '+faststart', phone])
    common.say(f'copia para el celu: {phone}')


if __name__ == '__main__':
    main()
