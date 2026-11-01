import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8')

test('endereco de compartilhamento presentation permanece publico e alias legado continua', async () => {
  const router = await read('src/router.tsx')
  const presentation = router.match(/const presentationRoute = createRoute\(\{[\s\S]*?\n\}\)/)?.[0] ?? ''
  assert.match(presentation, /path:\s*["']\/presentation["']/)
  assert.match(presentation, /component:\s*PresentationPage/)
  assert.doesNotMatch(presentation, /beforeLoad:\s*requireAdmin/)
  const legacy = router.match(/const legacyPresentationRoute = createRoute\(\{[\s\S]*?\n\}\)/)?.[0] ?? ''
  assert.match(legacy, /path:\s*["']\/apresentacao["']/)
  assert.match(legacy, /redirect\(\{\s*to:\s*["']\/presentation["']/)
})

test('html inicial usa URL compartilhada de cada ambiente e imagem HTTPS', async () => {
  const html = await read('index.html')
  assert.doesNotMatch(html, /<meta\s+property="og:url"/)
  assert.doesNotMatch(html, /<link\s+rel="canonical"/)
  assert.match(html, /property="og:image" content="https:\/\/shopee-bot-fj0w\.onrender\.com\/brand\/og-image\.png"/)
  assert.match(html, /name="twitter:card" content="summary_large_image"/)
  assert.match(html, /<meta name="description" content="[^"]+"/)
  const image = await readFile(new URL('../public/brand/og-image.png', import.meta.url))
  assert.ok(image.byteLength > 0)
})

test('robots nao oferece acesso privado /app para indexacao', async () => {
  const robots = await read('public/robots.txt')
  assert.match(robots, /Disallow:\s*\/app(?:\s|$)/m)
})
