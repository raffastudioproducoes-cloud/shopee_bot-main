import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = (path) => readFileSync(new URL(path, import.meta.url), 'utf8')
const { DISABLED_NETWORKS } = await import('../src/lib/networkLimits.ts')

test('X fica indisponivel no seletor ate virar plano pago', () => {
  const picker = source('../src/components/posts/NetworkPicker.tsx')
  assert.equal(DISABLED_NETWORKS.x, 'X estará disponível em um plano pago em breve')
  assert.match(picker, /em breve · plano pago/)
  assert.match(picker, /isNetworkDisabled\(key\)/)
  assert.match(picker, /const ready = availability === "active" && supported && !unavailable/)
  assert.match(picker, /disabled=\{disabled\}/)
})
