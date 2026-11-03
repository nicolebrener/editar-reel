"""Full-screen animated scenes that explain what is being said, built in HTML (no footage needed).

Each kind returns (markup, [gsap lines]). The scene covers the whole frame on a dark background, so the white
captions stay readable on top of it. Content sits between y 260 and y 1200: the captions live below that.

    chat       a conversation that writes itself            messages: [{"from": "me"|"them", "text", "t"}], title
    calendar   a week where free slots light up and tick     days, busy: [[day, slot]], free: [[day, slot]], times
    checklist  a list that ticks itself off                  items: ["..."], times, tags (optional, one per item)
    stat       a big number that counts up                   value, prefix, suffix, label
    text       a short statement, line by line               lines: ["..."], times; *word* goes in the accent colour
    upload     an AI chat: files drop in, a prompt is typed       files: [{"src", "dur"}], prompt, reply, title,
               and sent, the assistant answers                    times: {"files": [...], "type", "send", "reply"}

All times are seconds on the reel timeline; when they are missing, items follow each other every 0.45 s.
"""
import html
import re


def esc(s):
    return html.escape(str(s), quote=True)


def _times(it, n, gap=0.45, first=0.35):
    t = list(it.get('times') or [])
    while len(t) < n:
        t.append((t[-1] + gap) if t else it['start'] + first)
    return t


def chat(i, it, acc):
    msgs = it.get('messages', [])
    times = [m.get('t') for m in msgs]
    auto = _times({'start': it['start']}, len(msgs), gap=0.7)
    times = [t if t is not None else auto[k] for k, t in enumerate(times)]
    title = it.get('title', 'Chat')
    rows = ''.join(f'<div class="msg {"me" if m.get("from") == "me" else "them"} q{k}"><span>{esc(m["text"])}</span>'
                   f'<em>{esc(m.get("time", ""))}</em></div>' for k, m in enumerate(msgs))
    markup = (f'<div class="chat-hd"><div class="chat-av">{esc(title[:1].upper())}</div>'
              f'<div class="chat-who"><b>{esc(title)}</b><span>{esc(it.get("subtitle", "en línea"))}</span></div></div>'
              f'<div class="chat-body">{rows}</div>')
    js = [f'tl.fromTo("#{i} .q{k}",{{y:40,opacity:0,scale:0.94}},{{y:0,opacity:1,scale:1,duration:0.3,'
          f'ease:"back.out(1.8)"}},{t:.3f});' for k, t in enumerate(times)]
    return markup, js, times


CAL_EVENTS = ['Reunión', 'Llamada', 'Equipo', 'Cliente', 'Foco', 'Almuerzo', 'Daily', 'Entrega', 'Demo', 'Gym']
CAL_TINTS = ['#E2577F', '#E07A4F', '#9B7FD8', '#E8B53E', '#7FA86A']   # frambuesa, terracota, lavanda, mostaza, salvia


def calendar(i, it, acc):
    """A packed week: busy slots are coloured events with a name, free slots look empty until a search frame hops
    across the grid and lands on each one, which then lights up and ticks."""
    days = it.get('days', ['Lun', 'Mar', 'Mié', 'Jue', 'Vie'])
    slots = it.get('slots', 4)
    busy = {tuple(b) for b in it.get('busy', [])}
    free = [tuple(f) for f in it.get('free', [])]
    labels = it.get('labels') or CAL_EVENTS
    times = _times(it, len(free), gap=0.4, first=0.7)
    cols, order, n = '', [], 0
    for d, day in enumerate(days):
        cells = ''
        for s in range(slots):
            order.append((d, s))
            cid = f'c{d}-{s}'
            if (d, s) in busy:
                tint = CAL_TINTS[(d * 2 + s) % len(CAL_TINTS)]
                cells += (f'<div class="cell busy {cid}" style="--tint:{tint}"><span>{esc(labels[n % len(labels)])}'
                          f'</span></div>')
                n += 1
            elif (d, s) in free:
                cells += (f'<div class="cell empty free f{free.index((d, s))} {cid}"><svg viewBox="0 0 24 24">'
                          f'<polyline pathLength="1" points="5,12 10,17 19,7"/></svg></div>')
            else:
                cells += f'<div class="cell empty {cid}"></div>'
        cols += f'<div class="cal-col"><div class="cal-day">{esc(day)}</div>{cells}</div>'
    markup = (f'<div class="scn-title">{esc(it.get("title", "Tu semana"))}</div>'
              f'<div class="cal-grid">{cols}</div>')
    js = [f'tl.fromTo("#{i} .cal-col",{{y:30,opacity:0}},{{y:0,opacity:1,duration:0.3,stagger:0.06,'
          f'ease:"power3.out"}},{it["start"] + 0.1:.3f});',
          f'tl.fromTo("#{i} .cell.busy",{{scale:0.6,opacity:0}},{{scale:1,opacity:1,duration:0.22,stagger:0.025,'
          f'ease:"back.out(2)"}},{it["start"] + 0.2:.3f});']
    # the search frame: hops over a few busy cells before each free slot, as if checking them one by one
    prev = it['start'] + 0.55
    for k, t in enumerate(times):
        target = free[k]
        cands = [c for c in order if c in busy]
        hops = sorted(cands, key=lambda c: (abs(c[0] - target[0]) + abs(c[1] - target[1]), c))[:3][::-1]
        step = min(0.14, max(0.08, (t - prev) / (len(hops) + 1)))
        for h, c in enumerate(hops):
            ht = t - step * (len(hops) - h)
            js.append(f'tl.fromTo("#{i} .c{c[0]}-{c[1]}",{{boxShadow:"0 0 0 0px {acc}"}},'
                      f'{{boxShadow:"0 0 0 7px {acc}",duration:0.05,yoyo:true,repeat:1,repeatDelay:{max(0.0, step - 0.1):.3f}}},'
                      f'{ht:.3f});')
        js.append(f'tl.fromTo("#{i} .f{k}",{{backgroundColor:"rgba(255,255,255,0)",borderColor:"rgba(255,255,255,.12)",'
                  f'scale:1}},{{backgroundColor:"{acc}",borderColor:"{acc}",scale:1.08,duration:0.25,'
                  f'ease:"back.out(2)"}},{t:.3f});')
        js.append(f'tl.fromTo("#{i} .f{k} polyline",{{strokeDashoffset:1}},{{strokeDashoffset:0,duration:0.3}},'
                  f'{t + 0.1:.3f});')
        prev = t + 0.3
    return markup, js, times


def checklist(i, it, acc):
    items = it.get('items', [])
    tags = it.get('tags') or [''] * len(items)
    times = _times(it, len(items), gap=0.5, first=0.6)
    rows = ''.join(f'<div class="chk r{k}"><div class="box"><svg viewBox="0 0 24 24"><polyline pathLength="1" '
                   f'points="5,12 10,17 19,7"/></svg></div><span>{esc(t)}</span>'
                   f'{f"<i>{esc(tags[k])}</i>" if k < len(tags) and tags[k] else ""}</div>'
                   for k, t in enumerate(items))
    markup = f'<div class="scn-title">{esc(it.get("title", "Pendientes"))}</div><div class="chk-list">{rows}</div>'
    js = [f'tl.fromTo("#{i} .chk",{{x:-40,opacity:0}},{{x:0,opacity:1,duration:0.3,stagger:0.08,'
          f'ease:"power3.out"}},{it["start"] + 0.1:.3f});']
    for k, t in enumerate(times):
        js.append(f'tl.fromTo("#{i} .r{k} .box",{{backgroundColor:"rgba(255,255,255,0)"}},'
                  f'{{backgroundColor:"{acc}",duration:0.15}},{t:.3f});')
        js.append(f'tl.fromTo("#{i} .r{k} polyline",{{strokeDashoffset:1}},{{strokeDashoffset:0,duration:0.25}},'
                  f'{t + 0.05:.3f});')
        js.append(f'tl.to("#{i} .r{k} span",{{opacity:0.45,duration:0.2}},{t + 0.15:.3f});')
    return markup, js, times


def stat(i, it, acc):
    value = float(it.get('value', 0))
    decimals = 0 if value == int(value) else 1
    markup = (f'<div class="stat"><div class="stat-n"><span class="pre">{esc(it.get("prefix", ""))}</span>'
              f'<span class="stat-v">0</span><span class="suf">{esc(it.get("suffix", ""))}</span></div>'
              f'<div class="stat-l">{esc(it.get("label", ""))}</div></div>')
    t0 = it['start'] + 0.15
    js = [f'tl.fromTo("#{i} .stat",{{scale:0.85,opacity:0}},{{scale:1,opacity:1,duration:0.35,ease:"back.out(1.6)"}},'
          f'{it["start"]:.3f});']
    # the count-up is a fixed set of steps (one per frame, ease-out), so any frame renders the same when seeked
    count_for = it.get('countFor', 1.0)
    steps = max(2, int(count_for * 30))
    for s in range(steps + 1):
        f = 1 - (1 - s / steps) ** 3
        shown = f'{value * f:,.{decimals}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        js.append(f'tl.set("#{i} .stat-v",{{textContent:"{shown}"}},{t0 + count_for * s / steps:.3f});')
    js.append(f'tl.fromTo("#{i} .stat-l",{{y:20,opacity:0}},{{y:0,opacity:1,duration:0.3}},{t0 + 0.5:.3f});')
    return markup, js, [t0]


def text(i, it, acc):
    lines = it.get('lines', [])
    times = _times(it, len(lines), gap=0.5, first=0.1)

    def fmt(s):
        return re.sub(r'\*(.+?)\*', lambda m: f'<b style="color:{acc}">{m.group(1)}</b>', esc(s))
    rows = ''.join(f'<div class="tl l{k}">{fmt(s)}</div>' for k, s in enumerate(lines))
    markup = f'<div class="txt">{rows}</div>'
    js = [f'tl.fromTo("#{i} .l{k}",{{y:50,opacity:0}},{{y:0,opacity:1,duration:0.35,ease:"power3.out"}},{t:.3f});'
          for k, t in enumerate(times)]
    return markup, js, times


def burst(cls, color):
    """A starburst mark (rays of uneven length), the shape of the Claude logo."""
    import math
    lens = [46, 38, 47, 34, 44, 40, 47, 36, 45, 39, 46, 35]
    rays = ''.join(f'<line x1="50" y1="50" x2="{50 + L * math.cos(math.radians(k * 30 - 90)):.1f}" '
                   f'y2="{50 + L * math.sin(math.radians(k * 30 - 90)):.1f}"/>' for k, L in enumerate(lens))
    return (f'<svg class="{cls}" viewBox="0 0 100 100"><g stroke="{color}" stroke-width="9" stroke-linecap="round">'
            f'{rays}</g></svg>')


def upload(i, it, acc):
    """An AI chat app (warm dark, like the assistant apps): thumbnails of the clips drop in one by one, the prompt is
    typed in the input box, it is sent as a bubble with the files above it, and the assistant answers."""
    files = it.get('files', [])
    tm = it.get('times') or {}
    ft = list(tm.get('files') or [])
    while len(ft) < len(files):
        ft.append((ft[-1] + 0.12) if ft else it['start'] + 0.15)
    prompt = it.get('prompt', '')
    t_type = tm.get('type', (ft[-1] if ft else it['start']) + 0.3)
    t_send = tm.get('send', t_type + 0.05 * len(prompt) + 0.15)
    t_reply = tm.get('reply', t_send + 0.5)
    thumbs = ''.join(f'<div class="up-f f{k}"><img src="{esc(f["src"])}"><svg viewBox="0 0 24 24"><path d="M9 7v10l8-5z"/>'
                     f'</svg><em>{esc(f.get("dur", ""))}</em></div>' for k, f in enumerate(files))
    title = it.get('title', 'Claude')
    letters = ''.join(f'<i class="c{n}">{esc(ch) if ch != " " else "&nbsp;"}</i>' for n, ch in enumerate(prompt))
    mark = it.get('logo') == 'claude'
    hd = (burst('up-logo', '#D97757') if mark else '') + f'<span>{esc(title)}</span>'
    dot = burst('up-dot', '#D97757') if mark else '<span class="up-dot"></span>'
    markup = (f'<div class="up-hd">{hd}</div>'
              f'<div class="up-turn"><div class="up-files">{thumbs}</div>'
              f'<div class="up-msg">{esc(prompt)}</div></div>'
              f'<div class="up-reply">{dot}<span>{esc(it.get("reply", ""))}</span></div>'
              f'<div class="up-box"><div class="up-tray">{thumbs}</div><div class="up-line"><span class="up-typed">{letters}'
              f'</span><span class="up-ph">Escribí un mensaje</span><b class="up-send"><svg viewBox="0 0 24 24">'
              f'<path d="M12 19V5M6 11l6-6 6 6"/></svg></b></div></div>')
    js = []
    for k, t in enumerate(ft):   # the files land in the input box first
        js.append(f'tl.fromTo("#{i} .up-tray .f{k}",{{y:60,opacity:0,scale:0.7}},{{y:0,opacity:1,scale:1,'
                  f'duration:0.28,ease:"back.out(2)"}},{t:.3f});')
    # the prompt is typed letter by letter: every letter is already there, hidden, and shows up at its time (a
    # fromTo per letter, so seeking any frame shows the same text)
    step = max(0.03, min(0.07, (t_send - 0.12 - t_type) / max(1, len(prompt))))
    js.append(f'tl.fromTo("#{i} .up-ph",{{opacity:0.4}},{{opacity:0,duration:0.05}},{t_type:.3f});'
              f'tl.set("#{i} .up-ph",{{opacity:0}},{t_type + 0.05:.3f});')
    for n in range(len(prompt)):
        js.append(f'tl.fromTo("#{i} .up-typed .c{n}",{{opacity:0}},{{opacity:1,duration:0.01}},'
                  f'{t_type + step * (n + 1):.3f});')
    js += [f'tl.to("#{i} .up-send",{{scale:0.8,duration:0.08,yoyo:true,repeat:1}},{t_send - 0.1:.3f});',
           f'tl.to("#{i} .up-tray,#{i} .up-typed",{{opacity:0,duration:0.05}},{t_send:.3f});',
           f'tl.to("#{i} .up-ph",{{opacity:0.4,duration:0.05}},{t_send:.3f});',
           f'tl.fromTo("#{i} .up-turn",{{y:120,opacity:0}},{{y:0,opacity:1,duration:0.35,ease:"power3.out"}},'
           f'{t_send:.3f});',
           f'tl.fromTo("#{i} .up-reply",{{y:30,opacity:0}},{{y:0,opacity:1,duration:0.3,ease:"power2.out"}},'
           f'{t_reply:.3f});',
           f'tl.fromTo("#{i} .up-dot",{{rotation:0}},{{rotation:180,duration:0.6,ease:"power2.out"}},{t_reply:.3f});']
    return markup, js, ft[:1] + [t_send, t_reply]


KINDS = {'upload': upload, 'chat': chat, 'calendar': calendar, 'checklist': checklist, 'stat': stat, 'text': text}

CSS = """
.scn{position:absolute;inset:0;overflow:hidden;color:#fff;font-family:'Inter',sans-serif}
.scn-bg{position:absolute;inset:0;background:radial-gradient(120% 70% at 50% 30%,#2a2620 0%,#141311 55%,#0c0c0b 100%)}
.scn-bg:after{content:"";position:absolute;inset:0;background:radial-gradient(60% 40% at 80% 15%,var(--acc),transparent 70%);
  opacity:.14}
.scn-in{position:absolute;left:70px;right:110px;top:270px;bottom:640px;display:flex;flex-direction:column;
  justify-content:center;gap:40px}
.scn-title{font-weight:800;font-size:78px;letter-spacing:-1.5px;line-height:1}
.chat-hd{display:flex;align-items:center;gap:24px;padding-bottom:26px;border-bottom:2px solid rgba(255,255,255,.1)}
.chat-av{width:96px;height:96px;border-radius:50%;background:var(--acc);color:#141414;font-weight:800;font-size:46px;
  display:flex;align-items:center;justify-content:center}
.chat-who b{display:block;font-size:44px}.chat-who span{font-size:30px;opacity:.55;font-weight:600}
.chat-body{display:flex;flex-direction:column;gap:20px}
.msg{max-width:78%;padding:24px 30px;border-radius:34px;font-size:40px;font-weight:600;line-height:1.25;
  position:relative}
.msg em{display:block;font-style:normal;font-size:24px;opacity:.5;margin-top:6px;text-align:right}
.msg.them{align-self:flex-start;background:#26241f;border-bottom-left-radius:10px}
.msg.me{align-self:flex-end;background:var(--acc);color:#141414;border-bottom-right-radius:10px}
.cal-grid{display:flex;gap:16px}
.cal-col{flex:1;display:flex;flex-direction:column;gap:16px}
.cal-day{text-align:center;font-weight:800;font-size:36px;opacity:.7;margin-bottom:4px}
.cell{height:118px;border-radius:24px;display:flex;align-items:center;justify-content:center}
.cell.busy{background:color-mix(in srgb,var(--tint) 30%,#1d1b18);border-left:8px solid var(--tint);
  justify-content:flex-start;align-items:flex-start;padding:14px 12px}
.cell.busy span{font-size:24px;font-weight:800;color:#fff;opacity:.92;line-height:1.1}
.cell.empty{border:3px dashed rgba(255,255,255,.12)}
.cell svg,.box svg{width:56%;fill:none;stroke:#141414;stroke-width:3.4;stroke-linecap:round;stroke-linejoin:round}
.cell polyline,.box polyline{stroke-dasharray:1;stroke-dashoffset:1}
.chk-list{display:flex;flex-direction:column;gap:26px}
.chk{display:flex;align-items:center;gap:30px;background:#1f1d19;border-radius:30px;padding:30px 34px}
.chk .box{width:74px;height:74px;flex:none;border-radius:20px;border:4px solid var(--acc);display:flex;
  align-items:center;justify-content:center}
.chk span{font-size:44px;font-weight:700;flex:1}
.chk i{font-style:normal;font-size:28px;font-weight:800;color:#141414;background:var(--acc);padding:10px 18px;
  border-radius:16px}
.stat{display:flex;flex-direction:column;align-items:center;text-align:center;gap:16px}
.stat-n{font-weight:800;font-size:260px;letter-spacing:-8px;line-height:1;color:var(--acc)}
.stat-l{font-size:56px;font-weight:700;opacity:.85}
.txt{display:flex;flex-direction:column;gap:14px}
.scn-upload .scn-bg{background:#262624}.scn-upload .scn-bg:after{display:none}
.scn-upload .scn-in{justify-content:flex-start;gap:34px;bottom:620px}
.up-hd{display:flex;align-items:center;gap:20px;font-family:'DM Serif Display',serif;font-size:64px;opacity:.9;padding-bottom:22px;
  border-bottom:2px solid rgba(255,255,255,.08)}
.up-turn{opacity:0;display:flex;flex-direction:column;align-items:flex-end;gap:18px}
.up-files,.up-tray{display:flex;gap:14px;justify-content:flex-end}
.up-f{position:relative;width:150px;height:240px;border-radius:20px;overflow:hidden;background:#3a3934;
  border:2px solid rgba(255,255,255,.14)}
.up-f img{width:100%;height:100%;object-fit:cover}
.up-f svg{position:absolute;left:50%;top:44%;width:54px;margin-left:-27px;fill:#fff;opacity:.92;
  filter:drop-shadow(0 2px 6px rgba(0,0,0,.5))}
.up-f em{position:absolute;right:10px;bottom:8px;font-style:normal;font-size:22px;font-weight:700;
  text-shadow:0 1px 4px rgba(0,0,0,.7)}
.up-msg{background:#141413;padding:24px 34px;border-radius:30px;font-size:44px;font-weight:600}
.up-reply{opacity:0;display:flex;align-items:center;gap:20px;font-size:44px;font-weight:600}
.up-logo{width:70px;height:70px}
.up-dot{width:54px;height:54px;flex:none}span.up-dot{background:var(--acc);
  clip-path:polygon(50% 0,61% 39%,100% 50%,61% 61%,50% 100%,39% 61%,0 50%,39% 39%)}
.up-box{position:absolute;left:0;right:0;bottom:0;background:#30302e;border:2px solid rgba(255,255,255,.1);
  border-radius:36px;padding:22px 24px 22px 32px;display:flex;flex-direction:column;gap:18px}
.up-box .up-tray{justify-content:flex-start}.up-box .up-f{width:118px;height:190px;border-radius:16px}
.up-box .up-f svg{width:38px;margin-left:-19px}.up-box .up-f em{font-size:17px}
.up-line{position:relative;display:flex;align-items:center;min-height:76px;font-size:42px;font-weight:600}
.up-ph{position:absolute;left:0;opacity:.4}.up-typed i{font-style:normal;opacity:0}
.up-send{margin-left:auto;width:76px;height:76px;border-radius:22px;background:var(--acc);display:flex;
  align-items:center;justify-content:center}
.up-send svg{width:40px;fill:none;stroke:#fff;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}
.tl{font-weight:800;font-size:104px;letter-spacing:-2.5px;line-height:1.02}
"""
