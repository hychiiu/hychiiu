"""生成 README 用的终端动画 SVG（assets/terminal-light-v2.svg / terminal-dark-v2.svg）。

文字全部转成路径（JetBrains Mono + Noto Sans Mono CJK，均为 OFL），
因为 GitHub 以 <img> 渲染 SVG，无法加载网页字体。动画用 SMIL（打字、逐行出现、光标闪烁）。
用法：python3 tools/terminal.py [--accent LIGHT DARK] [--out DIR]   （依赖 fonttools）
  --accent  强调色（提示符、光标、高亮项），浅色 / 深色各一个，默认 ACCENT
  --out     输出目录，默认 assets/
"""
import argparse
from pathlib import Path
from fontTools.ttLib import TTFont, TTCollection
from fontTools.varLib import instancer
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

LATIN = '/usr/share/fonts/truetype/sand-box/google/JetBrains Mono/JetBrainsMono-VariableFont_wght.ttf'
CJK = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'  # index 7 = Noto Sans Mono CJK SC

# ---- 内容：(kind, text)。cmd 逐字打出；out 整行淡入。{k}/{v} 形式的行用 key 列对齐 ----
SCRIPT = [
    ('cmd', 'whoami'),
    ('out', '怀秋 · hychiiu'),
    ('cmd', 'echo $STACK'),
    ('list', ['*java', 'linux', 'docker']),  # * 开头的项用强调色
    ('cmd', 'echo $HOBBIES'),
    ('list', ['homelab', 'nas', 'networking', 'self-hosting', 'ai coding']),
    ('cmd', 'ls ~/links'),
    ('kv', ('blog', 'hychiiu.com')),
    ('kv', ('telegram', 't.me/inbluemoon')),
    ('kv', ('github', 'github.com/hychiiu')),
    ('kv', ('mail', 'i@hychiiu.com')),
    ('cmd', 'uptime'),
    ('dim', 'on github since 2017-04 · blog up since 2026-11-11'),
    ('prompt', ''),
]

# 唯一强调色：浅色 / 深色
ACCENT = {'light': '#2f7d4f', 'dark': '#78b588'}  # 柔和的终端绿

THEMES = {
    # 与博客 tokens.css 一致：纸色 / 深灰底，暖灰文字，唯一强调色（ACCENT）
    'light': dict(bg='#faf9f5', bar='#f3f2ee', border='#e3e1db', ink='#24231f', muted='#787670', faint='#a8a69f', dot='#d0cec6'),
    'dark': dict(bg='#18181a', bar='#1f1f21', border='#2c2c2f', ink='#f0efeb', muted='#a8a69f', faint='#787670', dot='#403f3a'),
}

FS = 14.0          # 拉丁字号
CELL = FS * 0.6    # 等宽单元 8.4px
LH = 24            # 行高
PAD_X, TOP, BAR = 28, 22, 38
W = 760
TYPE_MS, START_MS, AFTER_CMD_MS, LINE_MS = 55, 600, 260, 90

lat = instancer.instantiateVariableFont(TTFont(LATIN), {'wght': 400})
cjk = TTCollection(CJK).fonts[7]
fonts = [(lat, lat.getBestCmap(), lat.getGlyphSet(), FS / lat['head'].unitsPerEm),
         (cjk, cjk.getBestCmap(), cjk.getGlyphSet(), FS / cjk["head"].unitsPerEm * 1.08)]


def wide(ch):
    return ord(ch) >= 0x2E80 and ch not in '·—'


glyph_defs, glyph_ids = [], {}


def glyph(ch):
    """返回 (id, 单元数)；id=None 表示空格。"""
    if ch == ' ':
        return None, 1
    if ch in glyph_ids:
        return glyph_ids[ch]
    for font, cmap, gs, s in fonts:
        if ord(ch) in cmap:
            break
    else:
        raise SystemExit(f'missing glyph {ch!r}')
    cells = 2 if wide(ch) else 1
    name = cmap[ord(ch)]
    adv = font['hmtx'][name][0] * s
    dx = (cells * CELL - adv) / 2  # 在单元内居中
    pen = SVGPathPen(gs)
    gs[name].draw(TransformPen(pen, (s, 0, 0, -s, dx, 0)))
    gid = f'g{len(glyph_ids)}'
    d = pen.getCommands()
    if d:
        glyph_defs.append(f'<path id="{gid}" d="{d}"/>')
    glyph_ids[ch] = (gid if d else None, cells)
    return glyph_ids[ch]


def text(s, x, y, cls):
    out, col = [], 0
    for ch in s:
        gid, cells = glyph(ch)
        if gid:
            out.append(f'<use href="#{gid}" x="{x + col * CELL:.1f}" y="{y}"/>')
        col += cells
    return f'<g class="{cls}">{"".join(out)}</g>', col


def build(theme):
    glyph_defs.clear(); glyph_ids.clear()
    c = THEMES[theme]
    body, clips = [], []
    t = START_MS
    y = BAR + TOP - 14
    for i, (kind, val) in enumerate(SCRIPT):
        y += LH
        if kind in ('cmd', 'prompt'):
            p, pw = text('~ $', PAD_X, y, 'a')
            body.append(f'<g opacity="0">{p}<set attributeName="opacity" to="1" begin="{t}ms" fill="freeze"/></g>')
            x0 = PAD_X + (pw + 1) * CELL
            if kind == 'prompt':
                body.append(
                    f'<rect x="{x0:.1f}" y="{y - 12}" width="{CELL:.1f}" height="16" class="cur" opacity="0">'
                    f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1.1s" begin="{t}ms" repeatCount="indefinite"/></rect>')
                break
            g, n = text(val, x0, y, 'i')
            # 打字：裁切矩形宽度按字符离散增长
            vals = ';'.join(f'{k * CELL:.1f}' for k in range(n + 1))
            dur = TYPE_MS * n
            clips.append(
                f'<clipPath id="c{i}"><rect x="{x0:.1f}" y="{y - 16}" height="22" width="0">'
                f'<animate attributeName="width" values="{vals}" calcMode="discrete" dur="{dur}ms" begin="{t + 150}ms" fill="freeze"/></rect></clipPath>')
            body.append(f'<g clip-path="url(#c{i})">{g}</g>')
            # 打字时的光标
            body.append(
                f'<rect y="{y - 12}" width="{CELL:.1f}" height="16" class="cur" opacity="0" x="{x0:.1f}">'
                f'<set attributeName="opacity" to="1" begin="{t}ms"/>'
                f'<animate attributeName="x" values="{";".join(f"{x0 + k * CELL:.1f}" for k in range(n + 1))}" calcMode="discrete" dur="{dur}ms" begin="{t + 150}ms" fill="freeze"/>'
                f'<set attributeName="opacity" to="0" begin="{t + 150 + dur + 120}ms" fill="freeze"/></rect>')
            t += 150 + dur + AFTER_CMD_MS
        else:
            if kind == 'list':
                g, x = '', PAD_X + 2 * CELL
                for j, item in enumerate(val):
                    if j:
                        sep, n = text(' · ', x, y, 'f'); g += sep; x += n * CELL
                    hi = item.startswith('*')
                    part, n = text(item.lstrip('*'), x, y, 'a' if hi else 'i'); g += part; x += n * CELL
            elif kind == 'kv':
                k, v = val
                a, _ = text(k, PAD_X + 2 * CELL, y, 'm')
                b, _ = text(v, PAD_X + 12 * CELL, y, 'i')
                g = a + b
            else:
                g, _ = text(val, PAD_X + 2 * CELL, y, 'm' if kind == 'dim' else 'i')
            body.append(f'<g opacity="0">{g}<set attributeName="opacity" to="1" begin="{t}ms" fill="freeze"/></g>')
            t += LINE_MS
            nxt = SCRIPT[i + 1][0] if i + 1 < len(SCRIPT) else None
            if nxt in ('cmd', 'prompt'):
                y += 8; t += 260  # 命令组之间留一点白
    H = y + 26
    title, tw = text('i@hychiiu: ~', 0, 0, 'f')
    tx = (W - tw * CELL) / 2
    dots = ''.join(f'<circle cx="{22 + k * 18}" cy="{BAR / 2}" r="5.5" fill="{c["dot"]}"/>' for k in range(3))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t">
<title id="t">i@hychiiu — whoami: 怀秋 · hychiiu. stack: java, linux, docker. hobbies: homelab, nas, networking, self-hosting, ai coding. blog: hychiiu.com, telegram: t.me/inbluemoon, github: github.com/hychiiu, mail: i@hychiiu.com</title>
<style>.i{{fill:{c["ink"]}}}.m{{fill:{c["muted"]}}}.f{{fill:{c["faint"]}}}.a{{fill:{c["accent"]}}}.cur{{fill:{c["accent"]}}}</style>
<defs>{"".join(glyph_defs)}{"".join(clips)}</defs>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="{c["bg"]}" stroke="{c["border"]}"/>
<path d="M0.5 {BAR}V10.5a10 10 0 0 1 10-10h{W - 21}a10 10 0 0 1 10 10V{BAR}Z" fill="{c["bar"]}"/>
<path d="M0.5 {BAR}H{W - 0.5}" stroke="{c["border"]}"/>
{dots}<g transform="translate({tx:.1f} {BAR / 2 + 4.5})">{title}</g>
{"".join(body)}
</svg>
'''


ap = argparse.ArgumentParser()
ap.add_argument('--accent', nargs=2, metavar=('LIGHT', 'DARK'))
ap.add_argument('--out', type=Path, default=Path(__file__).resolve().parent.parent / 'assets')
args = ap.parse_args()
if args.accent:
    ACCENT.update(light=args.accent[0], dark=args.accent[1])
for th in THEMES:
    THEMES[th]['accent'] = ACCENT[th]
args.out.mkdir(parents=True, exist_ok=True)
for th in THEMES:
    out = args.out / f'terminal-{th}-v2.svg'
    out.write_text(build(th), encoding='utf-8')
    print(out, out.stat().st_size)
