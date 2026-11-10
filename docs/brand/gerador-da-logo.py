import json, math
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

FONT = TTFont('fonts/fontsource-poppins-5.3.0/package/files/poppins-latin-600-normal.woff2')
GS = FONT.getGlyphSet(); CM = FONT.getBestCmap()
CAP = FONT['OS/2'].sCapHeight or 700
class Custom:
    def __init__(self, width, fn): self.width = width; self.fn = fn
    def draw(self, pen): self.fn(pen)

def _r(pen):
    # r do original: ombro em arco (sem a quina reta no alto da haste), braço com corte vertical
    pen.moveTo((69, 0)); pen.lineTo((209, 0)); pen.lineTo((209, 276))
    pen.curveTo((209, 345), (262, 415), (342, 415))
    pen.lineTo((379, 415)); pen.lineTo((379, 562)); pen.lineTo((279, 562))
    pen.curveTo((159, 562), (69, 472), (69, 362)); pen.closePath()

def _b(pen):
    # b do original: a haste faz a curva e se funde à barriga embaixo (sem a ponta reta na base)
    pen.moveTo((69, 740)); pen.lineTo((209, 740)); pen.lineTo((209, 473))
    pen.qCurveTo((236, 513), (331, 563), (392, 563))
    pen.qCurveTo((463, 563), (578, 493), (645, 364), (645, 279))
    pen.qCurveTo((645, 194), (578, 63), (463, -9), (392, -9))
    pen.lineTo((279, -9)); pen.curveTo((159, -9), (69, 81), (69, 191)); pen.closePath()
    pen.moveTo((355, 440))
    pen.qCurveTo((317, 440), (250, 401), (209, 327), (209, 277))
    pen.qCurveTo((209, 227), (250, 153), (317, 114), (355, 114))
    pen.qCurveTo((394, 114), (461, 154), (502, 228), (502, 279))
    pen.qCurveTo((502, 329), (461, 402), (394, 440), (355, 440)); pen.closePath()

CUSTOM = {'r': Custom(404, _r), 'b': Custom(678, _b)}
def G(ch): return CUSTOM.get(ch) or GS[CM[ord(ch)]]
def adv(ch): return G(ch).width
def baked(ch, x, s):
    pen = SVGPathPen(GS, ntos=lambda v: f"{v:.2f}")
    G(ch).draw(TransformPen(pen, (s, 0, 0, -s, x * s, 0)))
    return pen.getCommands()

# ================================================================ NOME
def wordmark_svg(uid='w'):
    s = 0.1; track = -14
    x = 0.0; white_d = []; grad_d = []
    for ch in 'Auto':
        white_d.append(baked(ch, x, s)); x += adv(ch) + track
    R = CAP * 0.63; gap = 20
    ox = x + gap + R; planet = (ox, -CAP / 2 + 4, R)
    x = ox + R + gap + 4
    gx0 = x * s
    for ch in 'rbital':
        grad_d.append(baked(ch, x, s)); x += adv(ch) + track
    total = x * s
    px, py, pr = planet[0] * s, planet[1] * s, planet[2] * s
    top, bottom = -CAP * s - 20, 32
    sw = pr * 0.34
    rr = pr - sw / 2
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="-8 {top:.1f} {total + 18:.1f} {bottom - top:.1f}" role="img" aria-label="AutoOrbital">
  <defs>
    <linearGradient id="{uid}-w" x1="0" y1="-72" x2="0" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#d7daf3"/></linearGradient>
    <linearGradient id="{uid}-g" x1="{gx0:.1f}" y1="0" x2="{total:.1f}" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#2fa8ff"/><stop offset=".38" stop-color="#5a8bff"/><stop offset=".74" stop-color="#8f74f3"/><stop offset="1" stop-color="#b57cf7"/></linearGradient>
    <linearGradient id="{uid}-r" x1="{px-pr:.1f}" y1="{py-pr:.1f}" x2="{px+pr:.1f}" y2="{py+pr:.1f}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#7ff3ff"/><stop offset=".35" stop-color="#27b7ff"/><stop offset=".7" stop-color="#3a78ff"/><stop offset="1" stop-color="#8a6dff"/></linearGradient>
    <linearGradient id="{uid}-hi" x1="{px-pr:.1f}" y1="{py-pr:.1f}" x2="{px+pr*0.2:.1f}" y2="{py+pr*0.4:.1f}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></linearGradient>
    <linearGradient id="{uid}-sw" x1="{px-pr*1.75:.1f}" y1="0" x2="{px+pr*1.75:.1f}" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#ffffff" stop-opacity=".05"/><stop offset=".22" stop-color="#d6f6ff"/><stop offset=".55" stop-color="#6cc4ff"/><stop offset=".85" stop-color="#7a8bff"/><stop offset="1" stop-color="#9d7bff" stop-opacity=".1"/></linearGradient>
    <clipPath id="{uid}-front"><rect x="{px-pr*2:.1f}" y="{py:.1f}" width="{pr*4:.1f}" height="{pr*2:.1f}"/></clipPath>
    <filter id="{uid}-glow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="2.2"/></filter>
    <filter id="{uid}-glow2" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="4"/></filter>
  </defs>
  <path d="{' '.join(white_d)}" fill="url(#{uid}-w)"/>
  <circle cx="{px:.2f}" cy="{py:.2f}" r="{rr:.2f}" fill="none" stroke="#1ea8ff" stroke-width="{sw*1.1:.2f}" opacity=".55" filter="url(#{uid}-glow2)"/>
  <circle cx="{px:.2f}" cy="{py:.2f}" r="{rr:.2f}" fill="none" stroke="url(#{uid}-r)" stroke-width="{sw:.2f}"/>
  <circle cx="{px:.2f}" cy="{py:.2f}" r="{rr:.2f}" fill="none" stroke="url(#{uid}-hi)" stroke-width="{sw*0.38:.2f}" opacity=".9" transform="rotate(-8 {px:.2f} {py:.2f})"/>
  <circle cx="{px:.2f}" cy="{py:.2f}" r="{pr - sw:.2f}" fill="none" stroke="#c9f6ff" stroke-width=".8" opacity=".85"/>
  <ellipse cx="{px:.2f}" cy="{py:.2f}" rx="{pr*1.72:.2f}" ry="{pr*0.32:.2f}" fill="none" stroke="#5fc0ff" stroke-width="{pr*0.2:.2f}" opacity=".5" transform="rotate(-24 {px:.2f} {py:.2f})" filter="url(#{uid}-glow2)"/>
  <ellipse cx="{px:.2f}" cy="{py:.2f}" rx="{pr*1.72:.2f}" ry="{pr*0.32:.2f}" fill="none" stroke="url(#{uid}-sw)" stroke-width="{pr*0.085:.2f}" transform="rotate(-24 {px:.2f} {py:.2f})" opacity=".85"/>
  <ellipse cx="{px:.2f}" cy="{py:.2f}" rx="{pr*1.72:.2f}" ry="{pr*0.32:.2f}" fill="none" stroke="url(#{uid}-sw)" stroke-width="{pr*0.14:.2f}" transform="rotate(-24 {px:.2f} {py:.2f})" clip-path="url(#{uid}-front)" filter="url(#{uid}-glow)"/>
  <ellipse cx="{px:.2f}" cy="{py:.2f}" rx="{pr*1.72:.2f}" ry="{pr*0.32:.2f}" fill="none" stroke="#ffffff" stroke-width="{pr*0.05:.2f}" transform="rotate(-24 {px:.2f} {py:.2f})" clip-path="url(#{uid}-front)" opacity=".95"/>
  <path d="{' '.join(grad_d)}" fill="url(#{uid}-g)"/>
</svg>'''

# ================================================================ SÍMBOLO
def symbol_svg(animated=True, uid='s', full=True):
    cx, cy, tilt = 200, 206, -20
    def card(x, y, rot, kind, k, cls):
        w, h = (62, 48) if kind in ('video', 'image') else ((46, 56) if kind == 'doc' else (44, 40))
        icons = {
          'video': '<path d="M-5 -8 L9 0 L-5 8 Z" fill="#d7e6ff"/>',
          'image': '<circle cx="8" cy="-9" r="3.6" fill="#ffe0b8"/><path d="M-20 12 L-7 -4 L2 7 L8 1 L20 12 Z" fill="#a9c8ff"/>',
          'doc': '<rect x="-14" y="-17" width="28" height="3.2" rx="1.6" fill="#dbe8ff"/><rect x="-14" y="-8" width="28" height="3" rx="1.5" fill="#9fc0ff"/><rect x="-14" y="0" width="28" height="3" rx="1.5" fill="#9fc0ff"/><rect x="-14" y="8" width="18" height="3" rx="1.5" fill="#9fc0ff"/>',
          'mini': '<circle cx="6" cy="-6" r="3" fill="#ffe0b8"/><path d="M-15 11 L-5 -2 L2 6 L6 1 L15 11 Z" fill="#a9c8ff"/>'}
        return f'''
    <g class="ao-card {cls}" transform="translate({x} {y}) rotate({rot}) scale({k})">
      <rect x="{-w/2}" y="{-h/2}" width="{w}" height="{h}" rx="9" fill="url(#{uid}-card)" stroke="url(#{uid}-cardstroke)" stroke-width="2.6" filter="url(#{uid}-soft)"/>
      <rect x="{-w/2}" y="{-h/2}" width="{w}" height="{h}" rx="9" fill="none" stroke="#8fc2ff" stroke-width="1" opacity=".55"/>
      {icons[kind]}
    </g>'''
    cards = card(66, 198, -18, 'image', .62, 'c2') + card(322, 118, 13, 'video', .6, 'c1') + card(354, 226, 8, 'doc', .62, 'c3') + card(298, 290, -10, 'mini', .55, 'c4')

    # feixe de linhas finas do disco (coordenadas locais, giradas pelo tilt)
    strands_back, strands_front = [], []
    spec = [(160, 52, 1.2, .55, 'A'), (154, 49, 1.8, .8, 'A'), (148, 46, 1.4, .7, 'B'), (142, 44, 2.6, .95, 'A'), (136, 41, 1.6, .85, 'B'), (131, 39, 3.2, 1, 'B')]
    for rx, ry, sw, op, g in spec:
        e = f'<ellipse rx="{rx}" ry="{ry}" fill="none" stroke="url(#{uid}-disk{g})" stroke-width="{sw}" opacity="{op}"'
        strands_back.append(e + f' clip-path="url(#{uid}-back)"/>')
        strands_front.append(e + f' clip-path="url(#{uid}-front)"/>')
    hot = (f'<ellipse rx="128" ry="38" fill="none" stroke="url(#{uid}-hot)" stroke-width="9" opacity=".65" filter="url(#{uid}-blur4)" clip-path="url(#{uid}-front)"/>'
           f'<ellipse rx="128" ry="38" fill="none" stroke="url(#{uid}-hot)" stroke-width="3.4" clip-path="url(#{uid}-front)"/>'
           f'<ellipse rx="128" ry="38" fill="none" stroke="url(#{uid}-hotline)" stroke-width="1.3" clip-path="url(#{uid}-front)"/>')
    orbit = f'M -184 0 A 184 70 0 1 1 184 0 A 184 70 0 1 1 -184 0'
    sph = ('<animateMotion dur="11s" repeatCount="indefinite" path="%s"/>' % orbit) if animated else ''
    stars = ''.join(f'<circle class="ao-star" cx="{x}" cy="{y}" r="{r}" fill="#cfe0ff" style="animation-delay:{d}s"/>' for x, y, r, d in
        [(58,92,1.8,0),(118,48,1.4,.6),(350,160,1.5,1.1),(34,270,1.5,.3),(256,356,1.6,.9),(214,34,1.3,1.4),(372,306,1.3,.2),(92,350,1.3,1.0),(336,60,1.5,.5),(22,190,1.2,.8),(150,90,1.2,1.2),(296,70,1.2,.7)])
    vb = "0 0 400 400" if full else "18 24 364 364"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" role="img" aria-label="Auto Orbital">
  <defs>
    <radialGradient id="{uid}-bg" cx="50%" cy="52%" r="52%"><stop offset="0" stop-color="#2f6bff" stop-opacity=".22"/><stop offset=".5" stop-color="#1b2a8f" stop-opacity=".10"/><stop offset="1" stop-color="#0b1030" stop-opacity="0"/></radialGradient>
    <linearGradient id="{uid}-diskA" x1="-165" y1="0" x2="165" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#2f5bff"/><stop offset=".3" stop-color="#4f7bff"/><stop offset=".62" stop-color="#8a74ff"/><stop offset=".86" stop-color="#d58cff"/><stop offset="1" stop-color="#ff9ad6"/></linearGradient>
    <linearGradient id="{uid}-diskB" x1="-140" y1="0" x2="140" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#6f8cff"/><stop offset=".35" stop-color="#a9b8ff"/><stop offset=".7" stop-color="#e7c4ff"/><stop offset="1" stop-color="#ffd0e8"/></linearGradient>
    <linearGradient id="{uid}-hot" x1="-130" y1="0" x2="130" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#7ea0ff" stop-opacity="0"/><stop offset=".18" stop-color="#9db6ff" stop-opacity=".9"/><stop offset=".4" stop-color="#d9e6ff"/><stop offset=".58" stop-color="#ffffff"/><stop offset=".8" stop-color="#ffe2c8" stop-opacity=".95"/><stop offset="1" stop-color="#ffb8d8" stop-opacity="0"/></linearGradient>
    <linearGradient id="{uid}-hotline" x1="-130" y1="0" x2="130" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".25" stop-color="#fff" stop-opacity=".9"/><stop offset=".75" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
    <linearGradient id="{uid}-ring" x1="-80" y1="-30" x2="80" y2="40" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#2d63ff"/><stop offset=".3" stop-color="#58a6ff"/><stop offset=".6" stop-color="#e9e4ff"/><stop offset=".82" stop-color="#d68cff"/><stop offset="1" stop-color="#8a62ff"/></linearGradient>
    <linearGradient id="{uid}-orbit" x1="-184" y1="0" x2="184" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#4a63ff"/><stop offset=".5" stop-color="#2a3b9a"/><stop offset="1" stop-color="#a06bff"/></linearGradient>
    <linearGradient id="{uid}-card" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2c55d8" stop-opacity=".30"/><stop offset="1" stop-color="#18237a" stop-opacity=".42"/></linearGradient>
    <linearGradient id="{uid}-cardstroke" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#58a6ff"/><stop offset="1" stop-color="#7a6bff"/></linearGradient>
    <radialGradient id="{uid}-sphere" cx="35%" cy="35%" r="70%"><stop offset="0" stop-color="#bfe2ff"/><stop offset=".5" stop-color="#3b7bff"/><stop offset="1" stop-color="#1a2a99"/></radialGradient>
    <filter id="{uid}-blur8" x="-30%" y="-80%" width="160%" height="260%"><feGaussianBlur stdDeviation="7"/></filter>
    <filter id="{uid}-blur4" x="-30%" y="-80%" width="160%" height="260%"><feGaussianBlur stdDeviation="3.2"/></filter>
    <filter id="{uid}-blur3" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="3"/></filter>
    <filter id="{uid}-soft" x="-40%" y="-40%" width="180%" height="180%"><feDropShadow dx="0" dy="0" stdDeviation="5" flood-color="#2f6bff" flood-opacity=".7"/></filter>
    <clipPath id="{uid}-back"><rect x="-200" y="-100" width="400" height="101"/></clipPath>
    <clipPath id="{uid}-front"><rect x="-200" y="0" width="400" height="100"/></clipPath>
  </defs>
  <circle cx="200" cy="200" r="198" fill="url(#{uid}-bg)"/>
  <g transform="translate({cx} {cy}) rotate({tilt})">
    <ellipse rx="184" ry="70" fill="none" stroke="url(#{uid}-orbit)" stroke-width="1.3" opacity=".9"/>
    <ellipse rx="184" ry="70" fill="none" stroke="#5f6dff" stroke-width="4" opacity=".16" filter="url(#{uid}-blur3)"/>
    <g class="ao-disk-glow">{''.join(strands_back)}</g>
    <g><g>{sph}<circle r="7" fill="#3b7bff" opacity=".6" filter="url(#{uid}-blur3)"/><circle r="4.2" fill="url(#{uid}-sphere)"/></g></g>
  </g>
  <g transform="translate({cx} {cy})">
    <circle r="84" fill="none" stroke="#3f7bff" stroke-width="12" opacity=".38" filter="url(#{uid}-blur8)"/>
    <circle r="76" fill="none" stroke="url(#{uid}-ring)" stroke-width="9" opacity=".55" filter="url(#{uid}-blur4)"/>
    <circle r="76" fill="none" stroke="url(#{uid}-ring)" stroke-width="5"/>
    <circle r="76" fill="none" stroke="#ffffff" stroke-width="1.4" opacity=".75" stroke-dasharray="150 330" transform="rotate(-150)"/>
    <circle r="71" fill="#000"/>
    <path d="M 40 -58 A 71 71 0 0 1 70 12" fill="none" stroke="#ffb98a" stroke-width="3" opacity=".55" filter="url(#{uid}-blur3)"/>
  </g>
  <g transform="translate({cx} {cy}) rotate({tilt})"><g class="ao-disk-glow">{''.join(strands_front)}{hot}</g></g>
  <g transform="translate({cx} {cy}) rotate({tilt})"><circle cx="-160" cy="22" r="6" fill="#3b7bff" opacity=".5" filter="url(#{uid}-blur3)"/><circle cx="-160" cy="22" r="3.6" fill="url(#{uid}-sphere)"/></g>
  {cards if full else ''}
  {stars if full else ''}
</svg>'''

if False:
    open('out/simbolo.svg', 'w').write(symbol_svg(animated=False, uid='sym'))
    open('out/nome.svg', 'w').write(wordmark_svg(uid='nm'))
    sym, nm = symbol_svg(True, 'a'), wordmark_svg('b')
    html = open('out/preview.html').read()
    import re
    html = re.sub(r'<h2>Símbolo — em código \(animado\)</h2>.*?</svg></div>', f'<h2>Símbolo — em código (animado)</h2>{sym}</div>', html, flags=re.S)
    html = re.sub(r'<h2>Nome — em código</h2><div class="name">.*?</svg></div></div>', f'<h2>Nome — em código</h2><div class="name">{nm}</div></div>', html, flags=re.S)
    open('out/preview.html', 'w').write(html)
    print('ok', CAP)

STYLE = '''<style>
.ao-card{animation:ao-float 5s ease-in-out infinite}.c2{animation-delay:-1.2s}.c3{animation-delay:-2.4s}.c4{animation-delay:-3.4s}
@keyframes ao-float{0%,100%{translate:0 0}50%{translate:0 -5px}}
.ao-disk-glow{animation:ao-pulse 3.4s ease-in-out infinite}@keyframes ao-pulse{0%,100%{opacity:.85}50%{opacity:1}}
.ao-star{animation:ao-tw 2.6s ease-in-out infinite}@keyframes ao-tw{0%,100%{opacity:.25}50%{opacity:1}}
@media (prefers-reduced-motion:reduce){.ao-card,.ao-disk-glow,.ao-star{animation:none}}
</style>'''
def standalone(svg, animated=True):
    return svg.replace('>', '>' + (STYLE if animated else ''), 1)

if __name__ == '__main__':
    import os
    out = 'brand'
    open(f'{out}/logo-symbol.svg', 'w').write(standalone(symbol_svg(True, 'sy', True)))
    open(f'{out}/logo-mark.svg', 'w').write(standalone(symbol_svg(True, 'mk', False)))
    open(f'{out}/logo-mark-static.svg', 'w').write(symbol_svg(False, 'ms', False))
    open(f'{out}/logo-wordmark.svg', 'w').write(wordmark_svg('wm'))
    print('ok')
