"""Paso 4b: cuts the speaker out of the background, so titles can sit behind the head.

    PY scripts/cutout.py <project>          # run it in the background: ~1-3 min per 30 s on Apple Silicon,
                                            # much slower on Windows/Linux (CPU only)

Writes:
    assets/cutout.webm   aroll.mp4 with the background transparent (VP9 + alpha), same frames

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
        common.hf(['remove-background', aroll, '-o', cut, '--quality', 'balanced'], cwd=project)
    fa, fc = frames(aroll), frames(cut)
    if fa != fc:
        common.die(f'cutout.webm tiene {fc} frames y aroll.mp4 {fa}: no coinciden, volver a correr')
    common.say(f'OK cutout.webm ({fc} frames)')


if __name__ == '__main__':
    main()
