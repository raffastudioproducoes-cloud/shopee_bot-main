import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'

const root = (p) => new URL(`../${p}`, import.meta.url)
const read = (p) => readFileSync(root(p), 'utf8')

test('logo em código existe como SVG, sem fonte externa e respeitando movimento reduzido', () => {
  for (const f of ['logo-symbol', 'logo-mark', 'logo-mark-static', 'logo-wordmark']) {
    const svg = read(`public/brand/${f}.svg`)
    assert.match(svg, /^<svg /, f)
    assert.doesNotMatch(svg, /<image|font-family|href="http/, f)
  }
  for (const f of ['logo-symbol', 'logo-mark']) assert.match(read(`public/brand/${f}.svg`), /prefers-reduced-motion:reduce/, f)
})

test('o site usa a logo em código nos pontos de marca (sem os PNG antigos)', () => {
  const uses = {
    'src/pages/LoginPage.tsx': '/brand/logo-wordmark.svg',
    'src/pages/presentation/PresentationBody.tsx': '/brand/logo-wordmark.svg',
    'src/pages/presentation/Hero.tsx': '/brand/logo-mark.svg',
    'src/pages/PanelPage.tsx': '/brand/logo-mark-static.svg',
    'src/pages/AdminLayout.tsx': '/brand/logo-mark-static.svg',
    'src/components/ui/PostLoginSplash.tsx': '/brand/logo-mark.svg',
    'src/components/ui/OrbitalLoader.tsx': '/brand/logo-mark.svg',
    'index.html': '/brand/logo-mark.svg',
  }
  for (const [file, asset] of Object.entries(uses)) {
    const s = read(file)
    assert.ok(s.includes(asset), `${file} deve usar ${asset}`)
    assert.doesNotMatch(s, /brand\/(wordmark|symbol(-128)?)\.png/, `${file} ainda usa PNG antigo`)
  }
})

test('rasterizações da marca (PWA, favicon, social) existem e o favicon.ico foi refeito', () => {
  for (const f of ['symbol.png', 'symbol-128.png', 'wordmark.png', 'favicon-16.png', 'favicon-32.png', 'apple-touch-icon.png', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'og-image.png']) {
    assert.ok(existsSync(root(`public/brand/${f}`)), f)
  }
  assert.ok(existsSync(root('public/favicon.ico')))
})

test('apresentação: o planeta CSS foi trocado pelo buraco negro em código', () => {
  const hero = read('src/pages/presentation/Hero.tsx')
  assert.doesNotMatch(hero, /ao-planet|ao-orbit-ring/)
  assert.doesNotMatch(read('src/pages/presentation/Sections.tsx'), /ao-planet/)
})
