"""Builds a 3D LUT that converts iPhone HDR (HLG, BT.2020) to normal SDR video (Rec.709).

iPhones film HDR by default. Without this, the reel looks grey and washed out on Instagram.
ffmpeg's usual tone-mapping needs the zscale filter, which many ffmpeg builds lack, so we
compute the conversion ourselves and apply it with lut3d, which every build has.

Steps per LUT entry: HLG signal -> scene light -> HLG system gamma (1.2) -> exposure ->
BT.2020 to BT.709 gamut -> soft highlight roll-off -> BT.709 transfer.

    python make_lut.py out.cube [exposure]     # exposure 0.62 is a natural look; lower = darker
"""
import math
import os
import sys

SIZE = 33
A, B, C = 0.17883277, 0.28466892, 0.55991073
GAMUT = [[1.6605, -0.5876, -0.0728], [-0.1246, 1.1329, -0.0083], [-0.0182, -0.1006, 1.1187]]


def hlg_to_linear(e):
    return e * e / 3 if e <= 0.5 else (math.exp((e - C) / A) + B) / 12


REF = hlg_to_linear(0.75)  # HLG reference white


def rolloff(x, knee=0.55):
    if x <= knee:
        return x
    return knee + (1 - knee) * (1 - math.exp(-(x - knee) / (1 - knee)))


def bt709(x):
    x = max(0.0, x)
    return 4.5 * x if x < 0.018 else 1.099 * x ** 0.45 - 0.099


def write_lut(path, exposure=0.62):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    lines = [f'TITLE "HLG to Rec709 e{exposure}"', f'LUT_3D_SIZE {SIZE}']
    norm = REF * REF ** 0.2
    for b in range(SIZE):
        for g in range(SIZE):
            for r in range(SIZE):
                rgb = [hlg_to_linear(v / (SIZE - 1)) for v in (r, g, b)]
                y = 0.2627 * rgb[0] + 0.6780 * rgb[1] + 0.0593 * rgb[2]
                gain = (y ** 0.2 if y > 0 else 0) / norm * exposure
                rgb = [v * gain for v in rgb]
                rgb = [sum(GAMUT[i][j] * rgb[j] for j in range(3)) for i in range(3)]
                out = [min(1.0, bt709(rolloff(max(0.0, v)))) for v in rgb]
                lines.append('%.6f %.6f %.6f' % tuple(out))
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    return path


if __name__ == '__main__':
    write_lut(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.62)
    print('OK', sys.argv[1])
