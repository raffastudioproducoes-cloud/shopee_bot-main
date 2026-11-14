import assert from 'node:assert/strict'
import test from 'node:test'

const { validateForNetwork } = await import('../src/lib/networkLimits.ts')

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
