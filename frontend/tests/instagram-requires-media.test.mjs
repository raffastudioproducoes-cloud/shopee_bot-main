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
