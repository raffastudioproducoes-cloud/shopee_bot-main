import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { buildSync } from 'esbuild'

// Node 20 do CI não importa .ts: empacota com esbuild e importa em memória.
const load = (path) => {
  const { outputFiles } = buildSync({
    entryPoints: [fileURLToPath(new URL(`../src/${path}`, import.meta.url))],
    bundle: true, write: false, format: 'esm', platform: 'neutral', target: 'es2022',
  })
  return import(`data:text/javascript;base64,${Buffer.from(outputFiles[0].text).toString('base64')}`)
}
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), 'utf8')

const { NETWORK_RULES, validateForNetwork, productLimit, maxProductsFor } = await load('lib/networkLimits.ts')
const { planMediaComposition } = await load('lib/mediaComposition.ts')

const video = (durationSec = 20) => ({ name: 'v.mp4', size: 1000, kind: 'video', width: 1080, height: 1920, durationSec })
const draft = (over = {}) => ({ texts: ['oferta'], media: [video()], productCount: 1, ...over })
const errors = (network, d) => validateForNetwork(network, d).filter((i) => i.level === 'error')

test('regra do Shopee Vídeo espelha o backend (vídeo mp4 3–60 s, 150 caracteres, até 6 produtos)', () => {
  const rule = NETWORK_RULES.shopee_video
  assert.equal(rule.label, 'Shopee Vídeo')
  assert.equal(rule.requiresMedia, 'video')
  assert.deepEqual(rule.exts, ['mp4'])
  assert.deepEqual([rule.maxVideos, rule.maxImages, rule.maxGifs, rule.allowMix], [1, 0, 0, false])
  assert.deepEqual([rule.maxChars, rule.videoMinSec, rule.videoMaxSec, rule.maxProducts], [150, 3, 60, 6])
  assert.deepEqual(rule.deliveredModes, ['video'])
  assert.equal(rule.supportsTextOnly, false)
  assert.equal(rule.threadParts, false)
  for (const key of ['maxBytes', 'videoMaxSide', 'videoAspect']) assert.ok(rule.unverified.includes(key))
})

test('maxProducts: padrão 1 nas demais redes e limite do seletor é o maior entre as marcadas', () => {
  for (const network of ['threads', 'x', 'facebook', 'instagram', 'tiktok']) assert.equal(maxProductsFor(network), 1)
  assert.equal(productLimit([]), 1)
  assert.equal(productLimit(['threads', 'instagram']), 1)
  assert.equal(productLimit(['threads', 'shopee_video']), 6)
})

test('Shopee Vídeo aceita até 6 produtos e bloqueia o 7º com mensagem em português', () => {
  assert.equal(errors('shopee_video', draft({ productCount: 6 })).length, 0)
  const over = errors('shopee_video', draft({ productCount: 7 }))
  assert.deepEqual(over.map((i) => i.message), ['Shopee Vídeo aceita até 6 produtos por vídeo.'])
})

test('redes de 1 produto não bloqueiam com vários produtos: só avisam do corte automático', () => {
  const issues = validateForNetwork('threads', { texts: ['oi'], media: [], productCount: 3 })
  assert.equal(issues.filter((i) => i.level === 'error').length, 0)
  assert.match(issues.find((i) => i.key === 'maxProducts').message, /publicará apenas o 1º produto/)
  assert.equal(validateForNetwork('threads', { texts: ['oi'], media: [], productCount: 1 }).length, 0)
})

test('Shopee Vídeo exige vídeo de 3 a 60 s e legenda até 150 caracteres', () => {
  assert.ok(errors('shopee_video', draft({ media: [] })).some((i) => i.key === 'requiresMedia'))
  assert.ok(errors('shopee_video', draft({ media: [video(2)] })).some((i) => i.key === 'videoMinSec'))
  assert.ok(errors('shopee_video', draft({ media: [video(61)] })).some((i) => i.key === 'videoMaxSec'))
  assert.ok(errors('shopee_video', draft({ texts: ['a'.repeat(151)] })).some((i) => i.key === 'maxChars'))
})

test('composição informa quantos produtos cada rede recebe', () => {
  const d = draft({ productCount: 4 })
  assert.equal(planMediaComposition('shopee_video', d).productCount, 4)
  assert.equal(planMediaComposition('shopee_video', d).mode, 'video')
  assert.equal(planMediaComposition('tiktok', d).productCount, 1)
  assert.equal(planMediaComposition('threads', { texts: ['oi'], media: [], productCount: 0 }).productCount, 0)
})

test('seletor de produtos vira múltiplo com contador e ordem; acima do limite avisa sem apagar', () => {
  const picker = source('components/posts/PostProductPicker.tsx')
  const composer = source('components/posts/PostComposer.tsx')
  assert.match(picker, /`\$\{selectedIds\.length\} de \$\{limit\} produtos`/)
  assert.match(picker, /As redes selecionadas usarão só o 1º produto\./)
  assert.match(picker, /disabled=\{order === 0 && full\}/)
  assert.match(picker, /post-product-picker-order/)
  assert.match(composer, /const maxSelectableProducts = productLimit\(/)
  assert.match(composer, /limit=\{maxSelectableProducts\}/)
  assert.match(composer, /\.slice\(0, productLimit\(restoredNetworks\)\)/)
  assert.doesNotMatch(composer, /prev\.includes\(id\) \? \[\] : \[id\]/)
})

test('compositor lê credentials.shopee_video e usa /shopee-video/status como fallback', () => {
  const composer = source('components/posts/PostComposer.tsx')
  const picker = source('components/posts/NetworkPicker.tsx')
  assert.match(composer, /!credentials\.shopee_video/)
  assert.match(composer, /queryFn: shopeeVideoApi\.status/)
  assert.match(composer, /status\.needs_reconnect \|\| !status\.token_valid/)
  assert.match(picker, /"shopee_video"\]/)
  assert.match(picker, /key === "shopee-video" \? "shopee_video" : key/)
})
