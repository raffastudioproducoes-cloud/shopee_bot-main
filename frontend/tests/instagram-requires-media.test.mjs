import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

// Node 20 do CI não importa .ts: transpila e executa num contexto isolado.
const transpiled = ts.transpileModule(
  readFileSync(new URL('../src/lib/networkLimits.ts', import.meta.url), 'utf8'),
  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } },
).outputText
const mod = { exports: {} }
vm.runInNewContext(transpiled, { module: mod, exports: mod.exports })
const { validateForNetwork } = mod.exports

const errors = (draft) =>
  validateForNetwork('instagram', draft).filter((i) => i.key === 'requiresMedia' && i.level === 'error')

test('Instagram sem midia e erro mesmo com produto selecionado (API nao publica so texto)', () => {
  assert.equal(errors({ texts: ['oi'], media: [], productCount: 0 }).length, 1)
  assert.equal(errors({ texts: ['oi'], media: [], productCount: 1 }).length, 1)
  assert.match(errors({ texts: ['oi'], media: [], productCount: 1 })[0].message, /exige imagem ou vídeo/)
})

test('Instagram com imagem (inclusive foto Shopee importada) passa', () => {
  const media = [{ name: 'shopee-1.jpg', size: 1, kind: 'image' }]
  assert.equal(errors({ texts: ['oi'], media, productCount: 1 }).length, 0)
})

test('Instagram: vídeo fora de 9:16 só avisa (Reels), 9:16 não avisa', () => {
  const aspect = (width, height) => validateForNetwork('instagram', {
    texts: ['oi'], media: [{ name: 'v.mp4', size: 1000, kind: 'video', width, height, durationSec: 10 }], productCount: 0,
  }).filter((i) => i.key === 'reelsAspect')
  assert.equal(aspect(1080, 1920).length, 0)
  assert.equal(aspect(720, 1280).length, 0)
  const wide = aspect(1920, 1080)
  assert.equal(wide.length, 1)
  assert.equal(wide[0].level, 'warn')
  assert.match(wide[0].message, /9:16/)
})
