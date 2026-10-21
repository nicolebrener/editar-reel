"""Animated line icons that illustrate what is being said ("calendario" -> a calendar that ticks a day).

Each icon is an SVG on a 100x100 grid. Classes inside the SVG:
    d   line drawn on in white (or `color`)
    k   line drawn on afterwards in the accent colour (a check, a trend line)
    p   small filled dots that pop in after the drawing
    m   the part that keeps moving while the icon is on screen (hands, dots, a clapper)
MOTION adds that loop. build.py draws every line with stroke-dashoffset (pathLength="1").

Which icon fits which words lives in references/animaciones.md, so Claude can pick by meaning.
"""

def _p(tag, **a):
    """A drawable SVG element: pathLength=1 lets every line draw on with the same dash values."""
    attrs = ' '.join(f'{k.rstrip("_")}="{v}"' for k, v in a.items())
    return f'<{tag} pathLength="1" {attrs}/>'


ICONS = {
    'calendar': ''.join([
        _p('rect', class_='d', x=14, y=20, width=72, height=66, rx=10),
        _p('line', class_='d', x1=14, y1=38, x2=86, y2=38),
        _p('line', class_='d', x1=34, y1=12, x2=34, y2=26),
        _p('line', class_='d', x1=66, y1=12, x2=66, y2=26),
        *(f'<circle class="p" cx="{x}" cy="{y}" r="4"/>' for x, y in ((32, 54), (50, 54), (68, 54), (32, 72), (50, 72))),
        _p('polyline', class_='k', points='60,71 67,78 82,61'),
    ]),
    'chat': ''.join([
        _p('path', class_='d', d='M18 22 H82 A8 8 0 0 1 90 30 V62 A8 8 0 0 1 82 70 H46 L28 86 V70 H18 '
                                 'A8 8 0 0 1 10 62 V30 A8 8 0 0 1 18 22 Z'),
        *(f'<circle class="p m" cx="{x}" cy="46" r="5"/>' for x in (34, 50, 66)),
    ]),
    'check': ''.join([
        _p('circle', class_='d', cx=50, cy=50, r=38),
        _p('polyline', class_='k', points='32,52 45,65 70,38'),
    ]),
    'clock': ''.join([
        _p('circle', class_='d', cx=50, cy=50, r=38),
        _p('line', class_='d m', x1=50, y1=50, x2=50, y2=24),
        _p('line', class_='d', x1=50, y1=50, x2=66, y2=50),
        '<circle class="p" cx="50" cy="50" r="4"/>',
    ]),
    'bell': '<g class="m">' + ''.join([
        _p('path', class_='d', d='M30 68 V46 A20 20 0 0 1 70 46 V68 L78 76 H22 Z'),
        _p('line', class_='d', x1=50, y1=18, x2=50, y2=26),
        '<circle class="p" cx="50" cy="84" r="5"/>',
    ]) + '</g>' + '<circle class="p" cx="74" cy="24" r="9" style="fill:var(--acc)"/>',
    'list': ''.join(
        _p('rect', class_='d', x=14, y=y, width=18, height=18, rx=4) +
        _p('line', class_='d', x1=44, y1=y + 9, x2=86, y2=y + 9) +
        _p('polyline', class_='k', points=f'18,{y + 9} 22,{y + 14} 29,{y + 4}')
        for y in (16, 42, 68)),
    'send': '<g class="m">' + ''.join([
        _p('path', class_='d', d='M12 48 L88 16 L66 86 L50 58 Z'),
        _p('line', class_='d', x1=50, y1=58, x2=88, y2=16),
    ]) + '</g>',
    'shield': ''.join([
        _p('path', class_='d', d='M50 10 L84 22 V46 C84 68 70 82 50 90 C30 82 16 68 16 46 V22 Z'),
        _p('polyline', class_='k', points='34,50 46,62 68,38'),
    ]),
    'lock': ''.join([
        _p('rect', class_='d', x=24, y=46, width=52, height=40, rx=8),
        _p('path', class_='d m', d='M36 46 V34 A14 14 0 0 1 64 34 V46'),
        '<circle class="p" cx="50" cy="64" r="5"/>',
    ]),
    'bulb': ''.join([
        _p('path', class_='d', d='M50 18 A24 24 0 0 1 64 62 V70 H36 V62 A24 24 0 0 1 50 18 Z'),
        _p('line', class_='d', x1=40, y1=79, x2=60, y2=79),
        _p('line', class_='d', x1=43, y1=87, x2=57, y2=87),
        *(_p('line', class_='k', x1=x1, y1=y1, x2=x2, y2=y2)
          for x1, y1, x2, y2 in ((50, 4, 50, 10), (16, 14, 21, 19), (84, 14, 79, 19), (6, 42, 13, 42), (94, 42, 87, 42))),
    ]),
    'sparkle': ''.join([
        _p('path', class_='d', d='M44 14 C48 38 56 46 80 50 C56 54 48 62 44 86 C40 62 32 54 8 50 C32 46 40 38 44 14 Z'),
        '<g class="m">' + _p('path', class_='k', d='M80 10 C81 18 84 21 92 22 C84 23 81 26 80 34 '
                                                   'C79 26 76 23 68 22 C76 21 79 18 80 10 Z') + '</g>',
    ]),
    'chart': ''.join([
        _p('polyline', class_='d', points='14,14 14,86 86,86'),
        _p('polyline', class_='k', points='24,72 42,52 56,62 82,30'),
        _p('polyline', class_='k', points='68,30 82,30 82,44'),
    ]),
    'money': ''.join([
        _p('circle', class_='d', cx=50, cy=50, r=38),
        _p('path', class_='k', d='M62 36 C58 30 40 28 38 38 C36 48 64 46 62 58 C60 68 42 68 38 62'),
        _p('line', class_='k', x1=50, y1=24, x2=50, y2=76),
    ]),
    'search': '<g class="m">' + ''.join([
        _p('circle', class_='d', cx=42, cy=42, r=24),
        _p('line', class_='d', x1=60, y1=60, x2=84, y2=84),
    ]) + '</g>',
    'mail': ''.join([
        _p('rect', class_='d', x=12, y=24, width=76, height=54, rx=8),
        _p('polyline', class_='d', points='14,28 50,56 86,28'),
        '<circle class="p" cx="84" cy="24" r="9" style="fill:var(--acc)"/>',
    ]),
    'heart': '<g class="m">' + _p('path', class_='d', d='M50 84 C22 64 12 48 12 34 A18 18 0 0 1 50 26 '
                                                          'A18 18 0 0 1 88 34 C88 48 78 64 50 84 Z') + '</g>',
    'phone': ''.join([
        _p('rect', class_='d', x=28, y=8, width=44, height=84, rx=10),
        _p('line', class_='d', x1=44, y1=82, x2=56, y2=82),
        '<circle class="p m" cx="70" cy="14" r="9" style="fill:var(--acc)"/>',
    ]),
    'user': ''.join([
        _p('circle', class_='d', cx=50, cy=34, r=16),
        _p('path', class_='d', d='M20 86 C24 66 36 58 50 58 C64 58 76 66 80 86'),
    ]),
    'robot': ''.join([
        _p('rect', class_='d', x=18, y=30, width=64, height=50, rx=12),
        _p('line', class_='d', x1=50, y1=30, x2=50, y2=16),
        '<circle class="p" cx="50" cy="13" r="5"/>',
        '<g class="m">' + _p('line', class_='k', x1=36, y1=50, x2=36, y2=58) +
        _p('line', class_='k', x1=64, y1=50, x2=64, y2=58) + '</g>',
        _p('line', class_='d', x1=40, y1=68, x2=60, y2=68),
    ]),
}

# the loop each icon keeps while on screen: (target inside the icon, gsap vars, seconds per cycle).
# Every loop goes back and forth (yoyo) and ends at rest, except a full turn (rotation:360), which just repeats.
MOTION = {
    'chat': ('.m', '{y:-7,stagger:0.12,ease:"sine.inOut"}', 0.35),
    'clock': ('.m', '{rotation:360,svgOrigin:"50 50",ease:"none"}', 1.6),
    'bell': ('.m', '{rotation:14,svgOrigin:"50 18",ease:"sine.inOut"}', 0.18),
    'send': ('.m', '{x:6,y:-6,ease:"sine.inOut"}', 0.5),
    'lock': ('.m', '{y:-9,ease:"power2.out"}', 0.4),
    'sparkle': ('.m', '{scale:0.55,svgOrigin:"80 22",ease:"sine.inOut"}', 0.4),
    'search': ('.m', '{x:8,y:-6,ease:"sine.inOut"}', 0.45),
    'heart': ('.m', '{scale:1.12,svgOrigin:"50 55",ease:"sine.inOut"}', 0.3),
    'phone': ('.m', '{scale:1.3,svgOrigin:"70 14",ease:"sine.inOut"}', 0.3),
    'robot': ('.m', '{scaleY:0.15,svgOrigin:"50 54",ease:"power1.inOut"}', 0.12),
}
