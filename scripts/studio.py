"""El estudio: la edición en vivo en el navegador, para elegir estilo, tipografías y colores mirando el reel.

    PY scripts/studio.py <project> [--port 4321] [--open]

Starts a local server (only on 127.0.0.1) and prints its URL. The page plays the reel exactly as build.py draws it,
with the controls of assets/studio/options.json next to it. Every change is written to reel.json, build.py runs
again (under a second) and the preview reloads at the same moment of the reel. "Renderizar 4K" runs the final
render (2160x3840) and check.py, and leaves a new version in renders/ (never overwrites one).

Big videos (the 4K aroll, the cutout) play in the preview from small proxies in work/preview/; the render always
uses the originals. The first time a reel opens, making those proxies takes a few seconds.
"""
import argparse
import glob
import hashlib
import http.server
import json
import os
import re
import shutil
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

STUDIO = os.path.join(common.SKILL_DIR, 'assets', 'studio')
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
PROXY_W = 720
TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
         '.mp4': 'video/mp4', '.webm': 'video/webm', '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.png': 'image/png',
         '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.ttf': 'font/ttf', '.otf': 'font/otf',
         '.woff2': 'font/woff2', '.gif': 'image/gif', '.webp': 'image/webp'}


class Studio:
    def __init__(self, project):
        self.project = project
        self.name = os.path.basename(project.rstrip(os.sep))
        self.build_lock = threading.Lock()
        self.proxy_locks = {}
        self.widths = {}
        self.backed_up = False
        self.render = {'running': False, 'progress': 0, 'stage': '', 'log': [], 'out': None, 'phone': None,
                       'error': None}

    # ------------------------------------------------------------ project state
    def reel(self):
        return common.read_json(os.path.join(self.project, 'reel.json'), {})

    def duration(self):
        segs = common.read_json(os.path.join(self.project, 'segments.json'))
        return segs[-1]['end_frame'] / common.FPS

    def values(self, reel):
        """Effective value of every studio control: what reel.json says, else what build.py would use."""
        sys.path.insert(0, SCRIPTS)
        import importlib
        import build
        importlib.reload(build)   # build.py may have changed while the studio is open
        try:
            return build.studio_values(reel, common.load_config()) if hasattr(build, 'studio_values') else {}
        except SystemExit:        # an invalid value: build.py says why when it runs; the page keeps working
            return {}

    def renders(self):
        out = []
        for p in sorted(glob.glob(os.path.join(self.project, 'renders', '*.mp4')), key=os.path.getmtime, reverse=True):
            if p.endswith('-celu.mp4'):
                continue
            out.append({'name': os.path.basename(p), 'size': os.path.getsize(p),
                        'time': time.strftime('%d/%m %H:%M', time.localtime(os.path.getmtime(p)))})
        return out

    def build(self, preview=True):
        # --preview: the colour grade goes on the small proxies, not baked into the 4K videos (that takes minutes)
        with self.build_lock:
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'build.py'), self.project]
                               + (['--preview'] if preview else []), text=True,
                               capture_output=True, encoding='utf-8', errors='replace')
        return r.returncode == 0, (r.stdout + r.stderr).strip()

    def save_reel(self, reel):
        path = os.path.join(self.project, 'reel.json')
        if not self.backed_up and os.path.exists(path):
            # the reel as it was before this studio session, in case the person wants it back
            shutil.copy(path, os.path.join(self.project, 'work', time.strftime('reel-antes-del-estudio-%Y%m%d-%H%M.json')))
            self.backed_up = True
        common.write_json(path, reel)
        return self.build()

    # ------------------------------------------------------------ preview proxies
    def width(self, path):
        key = (path, os.path.getmtime(path))
        if key not in self.widths:
            try:
                self.widths[key] = common.video_info(path)['width']
            except SystemExit:
                self.widths[key] = 0
        return self.widths[key]

    def proxy(self, rel, grade=''):
        """A small copy of a video for the preview, with the reel's colour grade ("look:amount") when it has one."""
        src = os.path.join(self.project, rel)
        st = os.stat(src)
        key = hashlib.md5(f'{rel}|{st.st_mtime}|{st.st_size}|{grade}'.encode()).hexdigest()[:12]
        look = ''
        if grade:
            sys.path.insert(0, SCRIPTS)
            import importlib
            import build
            importlib.reload(build)
            name, k = grade.split(':')
            look = ',' + build.grade_filter(name, float(k), alpha=rel.endswith('.webm'))
        ext = os.path.splitext(rel)[1]
        out = os.path.join(self.project, 'work', 'preview', key + ext)
        lock = self.proxy_locks.setdefault(key, threading.Lock())
        with lock:
            if not os.path.exists(out):
                os.makedirs(os.path.dirname(out), exist_ok=True)
                tmp = out + '.tmp' + ext
                common.say(f'preparando la vista previa de {rel}')
                if ext == '.webm':   # keeps the alpha channel (the cutout)
                    cmd = ['ffmpeg', '-v', 'error', '-y', '-c:v', 'libvpx-vp9', '-i', src, '-vf', f'scale={PROXY_W}:-2{look}',
                           '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-b:v', '0', '-crf', '36', '-deadline',
                           'realtime', '-cpu-used', '8', '-row-mt', '1', '-g', '15', '-an', tmp]
                else:
                    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', f'scale={PROXY_W}:-2{look}', '-c:v', 'libx264',
                           '-preset', 'veryfast', '-crf', '22', '-g', '15', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
                           '-b:a', '160k', '-movflags', '+faststart', tmp]
                common.run(cmd)
                os.replace(tmp, out)
        return out

    def page(self):
        """index.html for the browser: the studio player, and big videos swapped for their proxies."""
        with open(os.path.join(self.project, 'index.html'), encoding='utf-8') as f:
            html = f.read()

        def swap(m):
            tag = m.group(0)
            rel = re.search(r'\bsrc="([^"]+)"', tag).group(1)
            grade = re.search(r'\bdata-grade="([^"]+)"', tag)
            path = os.path.join(self.project, rel)
            if rel.endswith(('.mp4', '.webm')) and os.path.exists(path) and (grade or self.width(path) > PROXY_W * 1.6):
                url = '/proxy/' + urllib.parse.quote(rel) + ('?g=' + urllib.parse.quote(grade.group(1)) if grade else '')
                return tag.replace(f'src="{rel}"', f'src="{url}"', 1)
            return tag

        html = re.sub(r'<video\b[^>]*>', swap, html)
        html = html.replace('<head>', '<head>\n<script>window.__timelines = {};</script>', 1)
        return html.replace('</body>', '<script src="/studio/player.js"></script>\n</body>', 1)

    # ------------------------------------------------------------ 4K render
    def next_output(self):
        n = 0
        for p in glob.glob(os.path.join(self.project, 'renders', f'{self.name}-v*.mp4')):
            m = re.search(r'-v(\d+)\.mp4$', p)
            n = max(n, int(m.group(1))) if m else n
        return f'renders/{self.name}-v{n + 1}.mp4'

    def start_render(self):
        if self.render['running']:
            return False
        self.render = {'running': True, 'progress': 0, 'stage': 'armando', 'log': [], 'out': None, 'phone': None,
                       'error': None}
        threading.Thread(target=self._render, daemon=True).start()
        return True

    def _log(self, line):
        self.render['log'] = (self.render['log'] + [line])[-60:]

    def _render(self):
        st = self.render
        try:
            st['stage'] = 'aplicando el color en 4K' if self.reel().get('grade') else 'armando'
            ok, log = self.build(preview=False)
            self._log(log)
            if not ok:
                raise RuntimeError('build.py falló')
            out = self.next_output()
            st['stage'] = 'renderizando en 4K'
            cmd = [common.npx(), '--yes', f'hyperframes@{common.HF_VERSION}', 'render', '-o', out, '--quality', 'high',
                   '--resolution', 'portrait-4k', '--crf', '14', '.']
            p = subprocess.Popen(cmd, cwd=self.project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # the CLI says "Capturing frame 491/1401" (or redraws "Frame 491/1401" in place, without newlines, in a
            # terminal): read raw chunks, not lines
            buf = ''
            while True:
                chunk = os.read(p.stdout.fileno(), 8192)
                if not chunk:
                    break
                buf += re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '\n', chunk.decode('utf-8', 'replace'))
                frames = re.findall(r'[Ff]rame (\d+)/(\d+)', buf)
                if frames and int(frames[-1][1]):
                    st['progress'] = min(0.97, int(frames[-1][0]) / int(frames[-1][1]))
                *lines, buf = buf.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not re.search(r'\[Render:trace\]|\[initSession|Browser:WARN|[Ff]rame \d+/\d+', line):
                        self._log(line)
            if p.wait() != 0:
                raise RuntimeError('el render falló')
            st['stage'] = 'controlando cortes y audio'
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'check.py'), self.project, out], text=True,
                               capture_output=True, encoding='utf-8', errors='replace')
            self._log((r.stdout + r.stderr).strip())
            st['out'] = os.path.basename(out)
            st['phone'] = os.path.basename(out).replace('.mp4', '-celu.mp4')
            st['progress'], st['stage'] = 1, 'listo'
        except Exception as e:  # noqa: BLE001
            st['error'] = str(e)
            st['stage'] = 'error'
        finally:
            st['running'] = False


def make_handler(studio):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send_json(self, data, code=200):
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def send_text(self, text, ctype):
            body = text.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def send_file(self, path):
            """Serves a file with Range support (the video element needs it to seek)."""
            if not os.path.isfile(path):
                return self.send_error(404)
            size = os.path.getsize(path)
            start, end = 0, size - 1
            rng = re.match(r'bytes=(\d*)-(\d*)', self.headers.get('Range', ''))
            if rng and (rng.group(1) or rng.group(2)):
                if rng.group(1):
                    start = int(rng.group(1))
                    end = int(rng.group(2)) if rng.group(2) else end
                else:
                    start = max(0, size - int(rng.group(2)))
                end = min(end, size - 1)
                self.send_response(206)
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            else:
                self.send_response(200)
            self.send_header('Content-Type', TYPES.get(os.path.splitext(path)[1].lower(), 'application/octet-stream'))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', str(end - start + 1))
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            with open(path, 'rb') as f:
                f.seek(start)
                left = end - start + 1
                try:
                    while left > 0:
                        chunk = f.read(min(1 << 20, left))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        left -= len(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        def inside(self, base, rel):
            path = os.path.realpath(os.path.join(base, rel))
            return path if path.startswith(os.path.realpath(base) + os.sep) else None

        def state(self):
            reel = studio.reel()
            return {'name': studio.name, 'skill': os.path.basename(common.SKILL_DIR), 'reel': reel,
                    'values': studio.values(reel), 'duration': studio.duration(), 'safe': common.SAFE,
                    'size': [common.W, common.H], 'renders': studio.renders(), 'render': studio.render,
                    'options': common.read_json(os.path.join(STUDIO, 'options.json'))}

        def do_GET(self):
            url = urllib.parse.urlparse(self.path)
            path = urllib.parse.unquote(url.path)
            if path in ('/', '/index.html'):
                return self.send_file(os.path.join(STUDIO, 'studio.html'))
            if path.startswith('/studio/'):
                p = self.inside(STUDIO, path[len('/studio/'):])
                return self.send_file(p) if p else self.send_error(404)
            if path == '/api/state':
                return self.send_json(self.state())
            if path == '/api/render':
                return self.send_json({'render': studio.render, 'renders': studio.renders()})
            if path == '/p/index.html':
                return self.send_text(studio.page(), 'text/html; charset=utf-8')
            if path.startswith('/p/'):
                p = self.inside(studio.project, path[3:])
                return self.send_file(p) if p else self.send_error(404)
            if path.startswith('/proxy/'):
                p = self.inside(studio.project, path[len('/proxy/'):])
                grade = urllib.parse.parse_qs(url.query).get('g', [''])[0]
                return self.send_file(studio.proxy(os.path.relpath(p, studio.project), grade)) if p else self.send_error(404)
            self.send_error(404)

        def do_POST(self):
            path = urllib.parse.urlparse(self.path).path
            body = self.rfile.read(int(self.headers.get('Content-Length') or 0))
            if path == '/api/reel':
                if studio.render['running']:
                    return self.send_json({'ok': False, 'log': 'esperá a que termine el render'}, 409)
                reel = json.loads(body or b'{}').get('reel')
                if not isinstance(reel, dict):
                    return self.send_json({'ok': False, 'log': 'reel inválido'}, 400)
                ok, log = studio.save_reel(reel)
                return self.send_json({'ok': ok, 'log': log, 'values': studio.values(reel)})
            if path == '/api/render':
                started = studio.start_render()
                return self.send_json({'ok': started, 'render': studio.render})
            if path == '/api/open':
                # opens the renders folder in Finder / Explorer
                folder = os.path.join(studio.project, 'renders')
                opener = {'macos': ['open'], 'windows': ['explorer']}.get(common.os_name(), ['xdg-open'])
                subprocess.Popen(opener + [folder])
                return self.send_json({'ok': True})
            self.send_error(404)

    return Handler


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--port', type=int, default=4321)
    ap.add_argument('--open', action='store_true', help='abrir el navegador')
    a = ap.parse_args()
    project = common.project_dir(a.project)
    for f in ('segments.json', 'aroll.mp4'):
        if not os.path.exists(os.path.join(project, f)):
            common.die(f'falta {f}: primero assemble.py')
    studio = Studio(project)
    ok, log = studio.build()
    common.say(log)
    if not ok:
        common.die('build.py falló: arreglá el error y volvé a abrir el estudio')
    server = None
    for port in range(a.port, a.port + 20):
        try:
            server = Server(('127.0.0.1', port), make_handler(studio))
            break
        except OSError:
            continue
    if server is None:
        common.die('no hay puertos libres')
    url = f'http://127.0.0.1:{server.server_address[1]}/'
    common.say(f'ESTUDIO {url}  (proyecto {studio.name}; Ctrl+C para cerrar)')
    if a.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
