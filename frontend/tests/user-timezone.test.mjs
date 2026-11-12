import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

// Transpila em memória: o CI roda Node 20, sem suporte nativo a .ts.
const source = readFileSync(new URL('../src/lib/userTimeZone.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.ESNext },
})
const tz = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)

test('valida nomes IANA e recusa lixo', () => {
  assert.equal(tz.isValidTimeZone('America/Sao_Paulo'), true)
  assert.equal(tz.isValidTimeZone('Asia/Tokyo'), true)
  assert.equal(tz.isValidTimeZone('Marte/Base'), false)
  assert.equal(tz.isValidTimeZone(''), false)
  assert.equal(tz.isValidTimeZone(null), false)
})

test('fuso do dispositivo vem do Intl e é válido', () => {
  const device = tz.deviceTimeZone()
  assert.equal(device, Intl.DateTimeFormat().resolvedOptions().timeZone)
  assert.equal(tz.isValidTimeZone(device), true)
})

test('só adota o fuso do dispositivo quando a conta nunca confirmou', () => {
  assert.equal(tz.shouldAdoptDeviceTimeZone({ timezone: 'America/Sao_Paulo', timezone_confirmed: false }, 'Europe/Lisbon'), true)
  assert.equal(tz.shouldAdoptDeviceTimeZone({ timezone: 'America/Sao_Paulo', timezone_confirmed: true }, 'Europe/Lisbon'), false)
  assert.equal(tz.shouldAdoptDeviceTimeZone({ timezone: 'Europe/Lisbon', timezone_confirmed: false }, 'Europe/Lisbon'), false)
  // API antiga (sem o campo) não dispara gravação.
  assert.equal(tz.shouldAdoptDeviceTimeZone({ timezone: 'America/Sao_Paulo' }, 'Europe/Lisbon'), false)
})

test('formata o mesmo instante no fuso escolhido', () => {
  tz.setUserTimeZone('America/Sao_Paulo')
  assert.equal(tz.formatUtcTimestamp('2026-07-01 13:00:00'), '01/07/2026, 10:00:00')
  tz.setUserTimeZone('Asia/Tokyo')
  assert.equal(tz.getUserTimeZone(), 'Asia/Tokyo')
  assert.equal(tz.formatUtcTimestamp('2026-07-01T13:00:00Z'), '01/07/2026, 22:00:00')
  tz.setUserTimeZone('Fuso/Invalido')
  assert.equal(tz.getUserTimeZone(), 'Asia/Tokyo')
  assert.equal(tz.formatUtcTimestamp('lixo'), 'Data inválida')
})

test('rótulo de recorrência traz o fuso', () => {
  assert.equal(tz.withTimeZone('09:00', 'America/Sao_Paulo'), '09:00 (America/Sao_Paulo)')
})

test('lista do seletor inclui o padrão e o fuso atual', () => {
  tz.setUserTimeZone('Europe/Lisbon')
  const zones = tz.supportedTimeZones()
  assert.ok(zones.includes('America/Sao_Paulo'))
  assert.ok(zones.includes('Europe/Lisbon'))
  assert.ok(zones.includes('UTC'))
})

test('telas usam o fuso do usuário, não Brasília fixo', () => {
  for (const file of ['pages/DashboardPage.tsx', 'pages/AnalyticsPage.tsx', 'components/posts/PostTimePicker.tsx']) {
    const source = readFileSync(new URL(`../src/${file}`, import.meta.url), 'utf8')
    assert.ok(!source.includes("'America/Sao_Paulo'"), file)
    assert.match(source, /getUserTimeZone|formatInstant/, file)
  }
  const composer = readFileSync(new URL('../src/components/posts/PostComposer.tsx', import.meta.url), 'utf8')
  assert.match(composer, /trigger: "cron"[^}]*timezone: getUserTimeZone\(\)/)
})
