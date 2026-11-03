"""Full-screen animated scenes that explain what is being said, built in HTML (no footage needed).

Each kind returns (markup, [gsap lines]). The scene covers the whole frame on a dark background, so the white
captions stay readable on top of it. Content sits between y 260 and y 1200: the captions live below that.

    chat       a conversation that writes itself            messages: [{"from": "me"|"them", "text", "t"}], title
    calendar   a week where free slots light up and tick     days, busy: [[day, slot]], free: [[day, slot]], times
    checklist  a list that ticks itself off                  items: ["..."], times, tags (optional, one per item)
    stat       a big number that counts up                   value, prefix, suffix, label
    text       a short statement, line by line               lines: ["..."], times; *word* goes in the accent colour

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


KINDS = {'chat': chat, 'calendar': calendar, 'checklist': checklist, 'stat': stat, 'text': text}

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
.tl{font-weight:800;font-size:104px;letter-spacing:-2.5px;line-height:1.02}
"""
