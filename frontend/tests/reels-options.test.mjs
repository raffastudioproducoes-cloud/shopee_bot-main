import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

// Node 20 do CI não importa .ts: transpila e executa num contexto isolado.
const transpiled = ts.transpileModule(
  readFileSync(new URL('../src/lib/reelsOptions.ts', import.meta.url), 'utf8'),
  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } },
).outputText
const mod = { exports: {} }
vm.runInNewContext(transpiled, { module: mod, exports: mod.exports })
const { facebookReelsEligibility, facebookReelsValue, FACEBOOK_REELS_REASON, INSTAGRAM_REELS_NOTE } = mod.exports

test('Facebook: vertical 9:16 de 3 a 90 s vem ligado por padrão', () => {
  const ok = facebookReelsEligibility({ width: 1080, height: 1920, durationSec: 30 })
  assert.equal(ok.allowed, true)
  assert.equal(ok.suggested, true)
  assert.equal(ok.reason, null)
  assert.equal(ok.warning, null)
  assert.equal(facebookReelsValue(null, ok), true)
  assert.equal(facebookReelsValue(false, ok), false) // o usuário pode desligar
})

test('Facebook: horizontal, curto ou longo fica desligado e travado com o motivo', () => {
  for (const video of [
    { width: 1920, height: 1080, durationSec: 30 },
    { width: 1080, height: 1080, durationSec: 30 }, // quadrado: 1 > 0,8
    { width: 1080, height: 1920, durationSec: 2 },
    { width: 1080, height: 1920, durationSec: 91 },
  ]) {
    const result = facebookReelsEligibility(video)
    assert.equal(result.allowed, false)
    assert.ok(result.reason.startsWith(FACEBOOK_REELS_REASON))
    assert.equal(facebookReelsValue(true, result), false)
  }
  assert.equal(FACEBOOK_REELS_REASON, 'Para Reels o vídeo precisa ser vertical 9:16 de 3 a 90 s')
})

test('Facebook: abaixo de 540x960 bloqueia; vertical fora de 9:16 só avisa', () => {
  assert.match(facebookReelsEligibility({ width: 480, height: 854, durationSec: 10 }).reason, /540×960/)
  const fourFive = facebookReelsEligibility({ width: 1080, height: 1350, durationSec: 10 })
  assert.equal(fourFive.allowed, true)
  assert.equal(fourFive.suggested, true)
  assert.match(fourFive.warning, /9:16/)
})

test('Facebook: vídeo sem metadados (produto) começa desligado mas pode ligar', () => {
  const unknown = facebookReelsEligibility(null)
  assert.equal(unknown.allowed, true)
  assert.equal(unknown.suggested, false)
  assert.equal(facebookReelsValue(null, unknown), false)
  assert.equal(facebookReelsValue(true, unknown), true)
})

test('Instagram fica travado como Reels e o Composer envia a escolha do Facebook', () => {
  assert.match(INSTAGRAM_REELS_NOTE, /sempre como Reels/)
  const panel = readFileSync(new URL('../src/components/posts/ReelsPublishPanel.tsx', import.meta.url), 'utf8')
  assert.match(panel, /<input type="checkbox" checked disabled \/> Instagram: Reels/)
  const composer = readFileSync(new URL('../src/components/posts/PostComposer.tsx', import.meta.url), 'utf8')
  assert.match(composer, /facebookReelsShown \? \{ facebook: facebookReels \} : undefined/)
  const page = readFileSync(new URL('../src/pages/CreatePostPage.tsx', import.meta.url), 'utf8')
  assert.match(page, /data\.reels\?\.\[network\] !== undefined \? \{ reels: data\.reels\[network\] \} : \{\}/)
  const planner = readFileSync(new URL('../src/components/campaigns/CampaignPlanner.tsx', import.meta.url), 'utf8')
  assert.match(planner, /facebook_reels: facebookReels/)
})
