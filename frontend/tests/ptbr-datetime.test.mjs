import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const { maskDate, maskTime, parseDate, parseTime, isoToBr } = await import('../src/lib/ptBrDateTime.ts')

test('maskDate insere as barras enquanto digita', () => {
  assert.equal(maskDate('1'), '1')
  assert.equal(maskDate('101'), '10/1')
  assert.equal(maskDate('10122026'), '10/12/2026')
  assert.equal(maskDate('10/12/2026999'), '10/12/2026')
  assert.equal(maskDate('ab12'), '12')
})

test('maskTime insere os dois pontos', () => {
  assert.equal(maskTime('2'), '2')
  assert.equal(maskTime('233'), '23:3')
  assert.equal(maskTime('2330'), '23:30')
  assert.equal(maskTime('23:30xx'), '23:30')
})

test('parseDate valida o calendário e devolve ISO', () => {
  assert.equal(parseDate('10/12/2026'), '2026-12-10')
  assert.equal(parseDate('29/02/2028'), '2028-02-29')
  assert.equal(parseDate('29/02/2027'), null)
  assert.equal(parseDate('31/04/2026'), null)
  assert.equal(parseDate('1/1/2026'), null)
  assert.equal(parseDate(''), null)
})

test('parseTime aceita 24h válidas', () => {
  assert.equal(parseTime('23:59'), '23:59')
  assert.equal(parseTime('00:00'), '00:00')
  assert.equal(parseTime('24:00'), null)
  assert.equal(parseTime('12:60'), null)
  assert.equal(parseTime('9:30'), null)
})

test('PostsPage usa campos pt-BR e botão em português (sem date/time nativos)', () => {
  const page = readFileSync(new URL('../src/pages/PostsPage.tsx', import.meta.url), 'utf8')
  assert.doesNotMatch(page, /type="(date|time|datetime-local)"/)
  assert.match(page, /placeholder="dd\/mm\/aaaa"/)
  assert.match(page, /Escolher arquivos/)
})

test('isoToBr converte aaaa-mm-dd em dd/mm/aaaa', () => {
  assert.equal(isoToBr('2026-10-13'), '13/10/2026')
})
