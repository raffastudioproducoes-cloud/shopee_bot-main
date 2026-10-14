import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8')
const manifest = JSON.parse(read('../public/manifest.webmanifest'))

test('manifest PWA instalável com identidade Auto Orbital', () => {
  assert.equal(manifest.name, 'Auto Orbital')
  assert.equal(manifest.short_name, 'Auto Orbital')
  assert.equal(manifest.theme_color, '#010719')
  assert.equal(manifest.display, 'standalone')
  assert.equal(manifest.scope, '/')
  const has = (size, purpose) => manifest.icons.some((i) => i.sizes === size && i.purpose === purpose)
  assert.ok(has('192x192', 'any'))
  assert.ok(has('512x512', 'any'))
  assert.ok(has('512x512', 'maskable'))
  for (const i of manifest.icons) readFileSync(new URL(`../public${i.src}`, import.meta.url))
})

test('index.html sem a marca antiga e com os metadados novos', () => {
  const html = read('../index.html')
  assert.doesNotMatch(html, /Shopee Auto Vendas/)
  assert.match(html, /<title>Auto Orbital<\/title>/)
  assert.match(html, /theme-color" content="#010719"/)
  assert.match(html, /rel="manifest" href="\/manifest.webmanifest"/)
  assert.match(html, /og:image" content="https:\/\//)
})

test('service worker ignora /api e não-GET', () => {
  const sw = read('../public/sw.js')
  assert.match(sw, /startsWith\('\/api\/'\)/)
  assert.match(sw, /method !== 'GET'/)
})
