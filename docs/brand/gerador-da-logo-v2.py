"""Logo Auto Orbital v2 (suave): buraco negro com disco em faixas difusas (sem traços marcados) e nome."""
from build3 import baked, adv, CAP

def annulus(R, r, k):
    return (f"M {-R} 0 A {R} {R*k:.2f} 0 1 1 {R} 0 A {R} {R*k:.2f} 0 1 1 {-R} 0 Z "
            f"M {-r} 0 A {r} {r*k:.2f} 0 1 0 {r} 0 A {r} {r*k:.2f} 0 1 0 {-r} 0 Z")

STYLE = '''<style>
.ao-card{animation:ao-float 7s ease-in-out infinite}.c2{animation-delay:-1.7s}.c3{animation-delay:-3.4s}.c4{animation-delay:-5.1s}
@keyframes ao-float{0%,100%{translate:0 0}50%{translate:0 -4px}}
.ao-disk{animation:ao-breathe 6s ease-in-out infinite}@keyframes ao-breathe{0%,100%{opacity:.88}50%{opacity:1}}
.ao-halo{animation:ao-halo 6s ease-in-out infinite}@keyframes ao-halo{0%,100%{opacity:.75}50%{opacity:1}}
.ao-star{animation:ao-tw 4.5s ease-in-out infinite}@keyframes ao-tw{0%,100%{opacity:.15}50%{opacity:.7}}
@media (prefers-reduced-motion:reduce){.ao-card,.ao-disk,.ao-halo,.ao-star{animation:none}}
</style>'''

def symbol_svg(uid='s', full=True, animated=True):
    cx, cy, tilt, k = 200, 206, -20, 0.30
    R, r, H = 176, 100, 68
    ann = annulus(R, r, k)
    glow = (f'<g class="ao-disk">'
            f'<path d="{annulus(R, r - 2, k)}" fill-rule="evenodd" fill="url(#{uid}-disk)" opacity=".30" filter="url(#{uid}-b12)"/>'
            f'<path d="{annulus(R - 14, r, k)}" fill-rule="evenodd" fill="url(#{uid}-disk)" opacity=".42" filter="url(#{uid}-b6)"/>'
            f'<path d="{annulus(R - 36, r, k)}" fill-rule="evenodd" fill="url(#{uid}-disk)" opacity=".62" filter="url(#{uid}-b3)"/>'
            f'<path d="{annulus(r + 22, r, k)}" fill-rule="evenodd" fill="url(#{uid}-disk2)" opacity=".8" filter="url(#{uid}-b2)"/></g>')
    front = (f'<g clip-path="url(#{uid}-front)"><g class="ao-disk">'
             f'<path d="{annulus(R - 14, r, k)}" fill-rule="evenodd" fill="url(#{uid}-diskF)" opacity=".42" filter="url(#{uid}-b6)"/>'
             f'<path d="{annulus(R - 36, r, k)}" fill-rule="evenodd" fill="url(#{uid}-diskF)" opacity=".62" filter="url(#{uid}-b3)"/>'
             f'<path d="{annulus(r + 22, r, k)}" fill-rule="evenodd" fill="url(#{uid}-diskF2)" opacity=".9" filter="url(#{uid}-b2)"/>'
             f'<ellipse rx="{r+5}" ry="{(r+5)*k:.2f}" fill="none" stroke="url(#{uid}-hot)" stroke-width="6" opacity=".7" filter="url(#{uid}-b3)"/>'
             f'<ellipse rx="{r+4}" ry="{(r+4)*k:.2f}" fill="none" stroke="url(#{uid}-hot)" stroke-width="1.8" filter="url(#{uid}-b1)"/></g></g>')
    def card(x, y, rot, kind, s, cls):
        w, h = (58, 44) if kind != 'doc' else (42, 52)
        ic = {'video': '<path d="M-5 -7 L8 0 L-5 7 Z" fill="#dfe9ff" opacity=".9"/>',
              'image': '<circle cx="8" cy="-8" r="3.2" fill="#ffe3c2" opacity=".9"/><path d="M-18 11 L-6 -3 L2 6 L8 1 L18 11 Z" fill="#b9d2ff" opacity=".85"/>',
              'doc': ''.join(f'<rect x="-11" y="{yy}" width="{ww}" height="2.6" rx="1.3" fill="#cfe0ff" opacity=".8"/>' for yy, ww in ((-14, 22), (-6, 22), (2, 22), (10, 14)))}[kind]
        return (f'<g class="ao-card {cls}"><g transform="translate({x} {y}) rotate({rot}) scale({s})">'
                f'<rect x="{-w/2}" y="{-h/2}" width="{w}" height="{h}" rx="11" fill="#3d6bff" opacity=".28" filter="url(#{uid}-b6)"/>'
                f'<rect x="{-w/2}" y="{-h/2}" width="{w}" height="{h}" rx="11" fill="url(#{uid}-card)" stroke="url(#{uid}-cardst)" stroke-width="1"/>{ic}</g></g>')
    cards = card(70, 196, -16, 'image', .6, 'c1') + card(318, 116, 12, 'video', .58, 'c2') + card(352, 232, 8, 'doc', .6, 'c3') + card(300, 300, -9, 'image', .5, 'c4')
    stars = ''.join(f'<circle class="ao-star" cx="{x}" cy="{y}" r="{rr}" fill="#dbe6ff" style="animation-delay:-{d}s"/>' for x, y, rr, d in
                    [(58,92,1.4,0),(118,50,1.1,1.1),(348,168,1.2,2.2),(36,268,1.2,.6),(254,352,1.3,1.7),(214,36,1,2.9),(370,304,1,.3),(94,346,1,2.0),(332,64,1.2,1.0)])
    orbit = f'M -186 0 A 186 {186*k+12:.1f} 0 1 1 186 0 A 186 {186*k+12:.1f} 0 1 1 -186 0'
    motion = f'<animateMotion dur="14s" repeatCount="indefinite" path="{orbit}"/>' if animated else ''
    vb = "0 0 400 400" if full else "20 26 360 360"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" role="img" aria-label="Auto Orbital">
  <defs>
    <radialGradient id="{uid}-bg" cx="50%" cy="52%" r="50%"><stop offset="0" stop-color="#3a6dff" stop-opacity=".26"/><stop offset=".55" stop-color="#2a2fa8" stop-opacity=".10"/><stop offset="1" stop-color="#0b1030" stop-opacity="0"/></radialGradient>
    <linearGradient id="{uid}-disk" x1="{-R}" y1="0" x2="{R}" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#2b5cff"/><stop offset=".3" stop-color="#5a86ff"/><stop offset=".58" stop-color="#9a7bff"/><stop offset=".82" stop-color="#e193ff"/><stop offset="1" stop-color="#ffb3d9"/></linearGradient>
    <linearGradient id="{uid}-disk2" x1="{-R}" y1="0" x2="{R}" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#4f7dff"/><stop offset=".3" stop-color="#8fb0ff"/><stop offset=".55" stop-color="#d9d2ff"/><stop offset=".8" stop-color="#ffc6f0"/><stop offset="1" stop-color="#ffd6e6"/></linearGradient>
    <linearGradient id="{uid}-diskF" x1="{-R}" y1="0" x2="{R}" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#2b5cff" stop-opacity="0"/><stop offset=".2" stop-color="#4f7dff" stop-opacity="0"/><stop offset=".34" stop-color="#6a8cff"/><stop offset=".58" stop-color="#9a7bff"/><stop offset=".68" stop-color="#c88cff"/><stop offset=".8" stop-color="#e193ff" stop-opacity="0"/><stop offset="1" stop-color="#ffb3d9" stop-opacity="0"/></linearGradient>
    <linearGradient id="{uid}-diskF2" x1="{-R}" y1="0" x2="{R}" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#4f7dff" stop-opacity="0"/><stop offset=".2" stop-color="#8fb0ff" stop-opacity="0"/><stop offset=".34" stop-color="#a9c0ff"/><stop offset=".55" stop-color="#e4dcff"/><stop offset=".68" stop-color="#ffd0f0"/><stop offset=".8" stop-color="#ffd6e6" stop-opacity="0"/><stop offset="1" stop-color="#ffd6e6" stop-opacity="0"/></linearGradient>
    <linearGradient id="{uid}-hot" x1="{-r}" y1="0" x2="{r}" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#8fb0ff" stop-opacity="0"/><stop offset=".22" stop-color="#b9cdff" stop-opacity=".9"/><stop offset=".5" stop-color="#ffffff"/><stop offset=".78" stop-color="#ffe6d2" stop-opacity=".9"/><stop offset="1" stop-color="#ffc0e0" stop-opacity="0"/></linearGradient>
    <linearGradient id="{uid}-ring" x1="-70" y1="-50" x2="70" y2="55" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#3a72ff"/><stop offset=".35" stop-color="#7fb4ff"/><stop offset=".62" stop-color="#f1ecff"/><stop offset=".85" stop-color="#c48bff"/><stop offset="1" stop-color="#7f6bff"/></linearGradient>
    <radialGradient id="{uid}-halo" cx="50%" cy="38%" r="60%"><stop offset="0" stop-color="#ffd9b8" stop-opacity=".9"/><stop offset=".5" stop-color="#b79bff" stop-opacity=".55"/><stop offset="1" stop-color="#4b74ff" stop-opacity=".35"/></radialGradient>
    <linearGradient id="{uid}-card" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3f67e6" stop-opacity=".30"/><stop offset="1" stop-color="#1d2a86" stop-opacity=".40"/></linearGradient>
    <linearGradient id="{uid}-cardst" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#9cc4ff" stop-opacity=".7"/><stop offset="1" stop-color="#8a7bff" stop-opacity=".25"/></linearGradient>
    <radialGradient id="{uid}-sph" cx="35%" cy="35%" r="70%"><stop offset="0" stop-color="#e3f1ff"/><stop offset=".5" stop-color="#5a8dff"/><stop offset="1" stop-color="#27349e"/></radialGradient>
    <filter id="{uid}-b12" x="-40%" y="-150%" width="180%" height="400%"><feGaussianBlur stdDeviation="11"/></filter>
    <filter id="{uid}-b6" x="-60%" y="-160%" width="220%" height="420%"><feGaussianBlur stdDeviation="6"/></filter>
    <filter id="{uid}-b2" x="-30%" y="-120%" width="160%" height="340%"><feGaussianBlur stdDeviation="1.3"/></filter>
    <filter id="{uid}-b3" x="-30%" y="-120%" width="160%" height="340%"><feGaussianBlur stdDeviation="2.6"/></filter>
    <filter id="{uid}-b1" x="-30%" y="-120%" width="160%" height="340%"><feGaussianBlur stdDeviation=".7"/></filter>
    <clipPath id="{uid}-back"><rect x="-240" y="-140" width="480" height="141"/></clipPath>
    <clipPath id="{uid}-front"><rect x="-240" y="0" width="480" height="140"/></clipPath>
  </defs>
  <circle cx="200" cy="200" r="198" fill="url(#{uid}-bg)"/>
  {stars if full else ''}
  <g transform="translate({cx} {cy}) rotate({tilt})">{glow}
    <g><g>{motion}<circle r="7" fill="#5a8dff" opacity=".55" filter="url(#{uid}-b6)"/><circle r="3.4" fill="url(#{uid}-sph)"/></g></g>
  </g>
  <g transform="translate({cx} {cy})">
    <g class="ao-halo">
      <circle r="{H+10}" fill="none" stroke="url(#{uid}-halo)" stroke-width="16" opacity=".42" filter="url(#{uid}-b12)"/>
      <circle r="{H+4}" fill="none" stroke="url(#{uid}-ring)" stroke-width="7" opacity=".7" filter="url(#{uid}-b3)"/>
      <circle r="{H+3}" fill="none" stroke="url(#{uid}-ring)" stroke-width="3" filter="url(#{uid}-b1)"/>
    </g>
    <circle r="{H}" fill="#000"/>
  </g>
  <g transform="translate({cx} {cy}) rotate({tilt})">{front}</g>
  {cards if full else ''}
</svg>'''

def wordmark_svg(uid='w'):
    s = 0.1; track = -14
    x = 0.0; white_d = []; grad_d = []
    for ch in 'Auto':
        white_d.append(baked(ch, x, s)); x += adv(ch) + track
    Rr = CAP * 0.60; gap = 26
    ox = x + gap + Rr
    px, py, pr = ox * s, (-CAP / 2 + 2) * s, Rr * s
    x = ox + Rr + gap + 2
    gx0 = x * s
    for ch in 'rbital':
        grad_d.append(baked(ch, x, s)); x += adv(ch) + track
    total = x * s
    top, bottom = -CAP * s - 22, 34
    sw = pr * 0.30; rr = pr - sw / 2
    A, B, k = pr * 1.78, pr * 1.2, 0.24
    ann = annulus(A, B, k)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="-8 {top:.1f} {total + 16:.1f} {bottom - top:.1f}" role="img" aria-label="AutoOrbital">
  <defs>
    <linearGradient id="{uid}-w" x1="0" y1="-72" x2="0" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#dfe2f6"/></linearGradient>
    <linearGradient id="{uid}-g" x1="{gx0:.1f}" y1="0" x2="{total:.1f}" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#3aa6ff"/><stop offset=".4" stop-color="#5f8dff"/><stop offset=".75" stop-color="#9076f5"/><stop offset="1" stop-color="#b784f8"/></linearGradient>
    <linearGradient id="{uid}-r" x1="{px-pr:.1f}" y1="{py-pr:.1f}" x2="{px+pr:.1f}" y2="{py+pr:.1f}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#8fe9ff"/><stop offset=".4" stop-color="#3fb0ff"/><stop offset=".75" stop-color="#4a7dff"/><stop offset="1" stop-color="#8f72ff"/></linearGradient>
    <linearGradient id="{uid}-d" x1="{-A:.1f}" y1="0" x2="{A:.1f}" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#bfe9ff" stop-opacity="0"/><stop offset=".2" stop-color="#d8f1ff"/><stop offset=".55" stop-color="#8fc4ff"/><stop offset=".85" stop-color="#a590ff"/><stop offset="1" stop-color="#b08cff" stop-opacity="0"/></linearGradient>
    <linearGradient id="{uid}-dw" x1="{-A:.1f}" y1="0" x2="{A:.1f}" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".3" stop-color="#fff" stop-opacity=".95"/><stop offset=".7" stop-color="#fff" stop-opacity=".8"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
    <clipPath id="{uid}-back"><rect x="{-A*1.2:.1f}" y="{-A:.1f}" width="{A*2.4:.1f}" height="{A + .5:.1f}"/></clipPath>
    <clipPath id="{uid}-front"><rect x="{-A*1.2:.1f}" y="0" width="{A*2.4:.1f}" height="{A:.1f}"/></clipPath>
    <filter id="{uid}-s" x="-50%" y="-200%" width="200%" height="500%"><feGaussianBlur stdDeviation=".55"/></filter>
    <filter id="{uid}-m" x="-50%" y="-200%" width="200%" height="500%"><feGaussianBlur stdDeviation="2.2"/></filter>
    <filter id="{uid}-l" x="-70%" y="-70%" width="240%" height="240%"><feGaussianBlur stdDeviation="4.5"/></filter>
  </defs>
  <path d="{' '.join(white_d)}" fill="url(#{uid}-w)"/>
  <g transform="translate({px:.2f} {py:.2f}) rotate(-22)" clip-path="url(#{uid}-back)" opacity=".8">
    <path d="{ann}" fill-rule="evenodd" fill="url(#{uid}-d)" opacity=".55" filter="url(#{uid}-m)"/>
    <path d="{ann}" fill-rule="evenodd" fill="url(#{uid}-d)" opacity=".8" filter="url(#{uid}-s)"/>
  </g>
  <circle cx="{px:.2f}" cy="{py:.2f}" r="{rr:.2f}" fill="none" stroke="#3aa6ff" stroke-width="{sw*1.2:.2f}" opacity=".42" filter="url(#{uid}-l)"/>
  <circle cx="{px:.2f}" cy="{py:.2f}" r="{rr:.2f}" fill="none" stroke="url(#{uid}-r)" stroke-width="{sw:.2f}"/>
  <g transform="translate({px:.2f} {py:.2f}) rotate(-22)" clip-path="url(#{uid}-front)">
    <path d="{ann}" fill-rule="evenodd" fill="url(#{uid}-d)" opacity=".6" filter="url(#{uid}-m)"/>
    <path d="{ann}" fill-rule="evenodd" fill="url(#{uid}-d)" filter="url(#{uid}-s)"/>
    <ellipse rx="{B + 1.2:.2f}" ry="{(B + 1.2) * k:.2f}" fill="none" stroke="url(#{uid}-dw)" stroke-width="1.1" filter="url(#{uid}-s)"/>
  </g>
  <path d="{' '.join(grad_d)}" fill="url(#{uid}-g)"/>
</svg>'''

def standalone(svg): return svg.replace('>', '>' + STYLE, 1)

if __name__ == '__main__':
    o = 'v2'
    open(f'{o}/logo-symbol.svg', 'w').write(standalone(symbol_svg('sy', True)))
    open(f'{o}/logo-mark.svg', 'w').write(standalone(symbol_svg('mk', False)))
    open(f'{o}/logo-mark-static.svg', 'w').write(symbol_svg('ms', False, animated=False))
    open(f'{o}/logo-wordmark.svg', 'w').write(wordmark_svg('wm'))
    print('ok')
