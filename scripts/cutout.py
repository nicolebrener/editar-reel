"""Paso 4b: cuts the speaker out of the background, so titles can sit behind the head.

    PY scripts/cutout.py <project>          # run it in the background: ~1-3 min per 30 s on Apple Silicon,
                                            # much slower on Windows/Linux (CPU only)

Writes:
    assets/cutout.webm   aroll.mp4 with the background transparent (VP9 + alpha), same frames and size

With a 4K aroll the mask is computed on a 1080 copy (4x faster) and then laid over the 4K frames, so the
pixels of the person stay 4K.

The mask can include things attached to the head (a ceiling lamp, a shelf). build.py handles that: during a
"behind" title only the cutout below a clip line covers the text.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


def frames(path):
    r = common.run(['ffprobe', '-v', 'error', '-count_packets', '-select_streams', 'v:0',
                    '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', path], capture=True)
    return int(r.stdout.strip().split(',')[0] or 0)


def main():
    if len(sys.argv) < 2:
        common.die('uso: cutout.py <project>')
    project = common.project_dir(sys.argv[1])
    aroll = os.path.join(project, 'aroll.mp4')
    cut = os.path.join(project, 'assets', 'cutout.webm')
    if not os.path.exists(cut) or os.path.getmtime(cut) < os.path.getmtime(aroll):
        common.say('recortando el fondo (tarda: corre en segundo plano)')
        info = common.video_info(aroll)
        if info['width'] <= common.W:
            common.hf(['remove-background', aroll, '-o', cut, '--quality', 'balanced'], cwd=project)
        else:
            small = os.path.join(project, 'work', 'cutout-src.mp4')
            mask = os.path.join(project, 'work', 'cutout-small.webm')
            fresh = os.path.exists(mask) and os.path.getmtime(mask) > os.path.getmtime(aroll)
            if not fresh:   # the mask is the slow part: reuse it when only the 4K pass has to run again
                common.run(['ffmpeg', '-v', 'error', '-y', '-i', aroll, '-vf',
                            f'scale={common.W}:{common.H}:flags=lanczos', '-c:v', 'libx264', '-preset', 'fast',
                            '-crf', '14', '-an', small])
                common.hf(['remove-background', small, '-o', mask, '--quality', 'balanced'], cwd=project)
            common.say('pasando el recorte a 4K')
            common.run(['ffmpeg', '-v', 'error', '-y', '-i', aroll, '-c:v', 'libvpx-vp9', '-i', mask, '-filter_complex',
                        f'[1:v]alphaextract,scale={info["width"]}:{info["height"]}:flags=bicubic[a];'
                        '[0:v][a]alphamerge,format=yuva420p[v]', '-map', '[v]', '-c:v', 'libvpx-vp9',
                        '-pix_fmt', 'yuva420p', '-b:v', '0', '-crf', '20', '-row-mt', '1', '-tile-columns', '2',
                        '-deadline', 'good', '-cpu-used', '4', '-frames:v', str(frames(aroll)), '-an',
                        cut + '.tmp.webm'])
            os.replace(cut + '.tmp.webm', cut)
    fa, fc = frames(aroll), frames(cut)
    if fa != fc:
        common.die(f'cutout.webm tiene {fc} frames y aroll.mp4 {fa}: no coinciden, volver a correr')
    common.say(f'OK cutout.webm ({fc} frames)')


if __name__ == '__main__':
    main()
