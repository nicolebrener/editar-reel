"""Checks and prepares everything /editar-reel needs. Safe to run again at any time.

Prints one STATUS line per item and READY at the end when everything works:
  1. ffmpeg + ffprobe on PATH
  2. Node.js 22+ (runs HyperFrames, the HTML-to-video renderer)
  3. A Python 3.10-3.13 venv inside the skill with faster-whisper + Pillow
  4. The sound effects (synthesized here with ffmpeg, so they are ours and free to share)
  5. The HDR -> SDR LUT

Run it with any Python 3: python3 scripts/setup.py
"""
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

FIX = {
    'ffmpeg': {'macos': 'brew install ffmpeg', 'linux': 'sudo apt install ffmpeg',
               'windows': 'winget install --id Gyan.FFmpeg -e'},
    'node': {'macos': 'brew install node', 'linux': 'https://nodejs.org (versión 22 o más nueva)',
             'windows': 'winget install --id OpenJS.NodeJS.LTS -e'},
    'python': {'macos': 'brew install python@3.12', 'linux': 'sudo apt install python3.12 python3.12-venv',
               'windows': 'winget install --id Python.Python.3.12 -e'},
}
OSN = common.os_name()
ok_all = True


def status(item, ok, detail=''):
    global ok_all
    ok_all = ok_all and ok
    common.say(f'STATUS {item} {"OK" if ok else "FALTA"}{" (" + detail + ")" if detail else ""}')


def check_ffmpeg():
    if shutil.which('ffmpeg') and shutil.which('ffprobe'):
        out = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True).stdout.split('\n')[0]
        status('ffmpeg', True, out.split(' ')[2] if len(out.split(' ')) > 2 else '')
    else:
        status('ffmpeg', False, 'instalar con: ' + FIX['ffmpeg'][OSN])


def check_node():
    node = shutil.which('node')
    if not node:
        return status('node', False, 'instalar con: ' + FIX['node'][OSN])
    v = subprocess.run([node, '--version'], capture_output=True, text=True).stdout.strip()
    major = int(re.findall(r'\d+', v)[0]) if v else 0
    status('node', major >= 22, v if major >= 22 else f'{v} es vieja, actualizar con: ' + FIX['node'][OSN])


def candidate_pythons():
    """faster-whisper needs Python 3.10-3.13 (3.14+ has no ctranslate2 wheels yet)."""
    names = ['python3.12', 'python3.13', 'python3.11', 'python3.10', 'python3', 'python']
    seen = []
    for n in names:
        p = shutil.which(n)
        if p and p not in seen:
            seen.append(p)
    for p in ['/opt/homebrew/bin/python3.12', '/usr/local/bin/python3.12']:
        if os.path.exists(p) and p not in seen:
            seen.append(p)
    if OSN == 'windows' and shutil.which('py'):
        for minor in (12, 13, 11, 10):
            r = subprocess.run(['py', f'-3.{minor}', '-c', 'import sys;print(sys.executable)'],
                               capture_output=True, text=True)
            if r.returncode == 0:
                seen.append(r.stdout.strip())
    good = []
    for p in seen:
        r = subprocess.run([p, '-c', 'import sys;print(sys.version_info[0], sys.version_info[1])'],
                           capture_output=True, text=True)
        if r.returncode == 0:
            major, minor = map(int, r.stdout.split())
            if major == 3 and 10 <= minor <= 13:
                good.append(p)
    return good


def venv_works(py):
    if not os.path.exists(py):
        return False
    r = subprocess.run([py, '-c', 'import faster_whisper, PIL; print("ok")'], capture_output=True, text=True)
    return r.returncode == 0


def check_venv():
    py = common.venv_python()
    if venv_works(py):
        return status('python-venv', True)
    bases = candidate_pythons()
    if not bases:
        return status('python-venv', False, 'hace falta Python 3.10 a 3.13, instalar con: ' + FIX['python'][OSN])
    venv = os.path.join(common.SKILL_DIR, '.venv')
    if os.path.exists(venv) and not venv_works(py):
        shutil.rmtree(venv)   # a broken venv we created ourselves; rebuilt below
    common.say(f'STATUS python-venv creando con {bases[0]} (faster-whisper + Pillow, ~1 min)')
    subprocess.run([bases[0], '-m', 'venv', venv], check=True)
    r = subprocess.run([py, '-m', 'pip', 'install', '-q', '--upgrade', 'pip', 'faster-whisper', 'Pillow'],
                       capture_output=True, text=True)
    if r.returncode != 0 or not venv_works(py):
        common.say((r.stdout or '')[-1500:] + (r.stderr or '')[-1500:])
        return status('python-venv', False, 'pip falló, ver arriba')
    status('python-venv', True)


# Each effect is a short ffmpeg recipe: synthesized, so no licence questions when sharing the repo.
SFX = {
    'pop': ("aevalsrc='0.9*exp(-28*t)*sin(2*PI*(260*t+700*(1-exp(-45*t))/45))':s=48000:d=0.14", ''),
    'click': ("aevalsrc='0.7*exp(-180*t)*sin(2*PI*2400*t)+0.3*exp(-90*t)*sin(2*PI*900*t)':s=48000:d=0.05", ''),
    'ding': ("aevalsrc='0.45*exp(-5*t)*(sin(2*PI*1320*t)+0.6*sin(2*PI*1980*t)+0.25*sin(2*PI*2640*t))':"
             "s=48000:d=0.7", ''),
    'rise': ("aevalsrc='0.5*sin(PI*t/0.3)*sin(2*PI*(380*t+900*t*t/0.6))':s=48000:d=0.3", ''),
    'bass': ("aevalsrc='0.95*exp(-7*t)*sin(2*PI*(48*t+60*(1-exp(-20*t))/20))':s=48000:d=0.5", ''),
    'whoosh': ("anoisesrc=d=0.45:c=pink:a=0.9:r=48000",
               ",bandpass=f=1400:width_type=h:w=2200,volume='sin(PI*t/0.45)^2':eval=frame,volume=2.2"),
}


def make_sfx():
    out_dir = os.path.join(common.SKILL_DIR, 'assets', 'sfx')
    os.makedirs(out_dir, exist_ok=True)
    made = 0
    for name, (src, extra) in SFX.items():
        out = os.path.join(out_dir, name + '.mp3')
        if os.path.exists(out):
            continue
        r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', src, '-af',
                            'aformat=channel_layouts=stereo' + extra + ',alimiter=limit=0.9',
                            '-c:a', 'libmp3lame', '-q:a', '3', out], capture_output=True, text=True)
        if r.returncode != 0:
            return status('sfx', False, r.stderr.strip()[:300])
        made += 1
    status('sfx', True, f'{len(SFX)} efectos' + (f', {made} nuevos' if made else ''))


GSAP_URL = 'https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/gsap.min.js'


def get_gsap():
    """GSAP animates the composition. Downloaded (not stored in the repo) and loaded locally at render time."""
    import urllib.request
    out = os.path.join(common.SKILL_DIR, 'assets', 'vendor', 'gsap.min.js')
    if not os.path.exists(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        try:
            urllib.request.urlretrieve(GSAP_URL, out)
        except Exception as e:  # noqa: BLE001
            return status('gsap', False, f'sin internet? {e}')
    status('gsap', os.path.getsize(out) > 10000)


def make_lut():
    cfg = common.load_config()
    try:
        common.hdr_lut_path(float(cfg.get('hdrExposure', 0.62)))
        status('lut-hdr', True)
    except Exception as e:  # noqa: BLE001
        status('lut-hdr', False, str(e))


if __name__ == '__main__':
    common.say(f'STATUS sistema {OSN} {os.uname().machine if hasattr(os, "uname") else ""}')
    check_ffmpeg()
    check_node()
    check_venv()
    if shutil.which('ffmpeg'):
        make_sfx()
    get_gsap()
    make_lut()
    cfg_ok = os.path.exists(common.CONFIG_PATH)
    common.say('STATUS config ' + ('OK' if cfg_ok else 'FALTA (Claude la crea con tus respuestas)'))
    common.say('READY' if ok_all else 'NOT READY')
