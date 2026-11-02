import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const source = (path) => readFile(new URL(`../src/${path}`, import.meta.url), 'utf8')

test('compositor só oferece agora e recorrente, com produto individual', async () => {
  const page = await source('pages/PostsPage.tsx')
  const picker = await source('components/posts/PostProductPicker.tsx')
  assert.match(page, /value: "now", label: "Agora"/)
  assert.match(page, /value: "cron", label: "Recorrente"/)
  assert.doesNotMatch(page, /value: "date", label: "Agendar"/)
  assert.match(picker, /type="radio"/)
  assert.doesNotMatch(picker, /onToggleList/)
})

test('validação de hora usa dígitos reais e controle 24h', async () => {
  const page = await source('pages/PostsPage.tsx')
  const picker = await source('components/posts/PostTimePicker.tsx')
  assert.ok(page.includes(String.raw`/^([01]\d|2[0-3]):[0-5]\d$/`),
    'Expressão HH:MM deve usar classe de dígitos, não barras literais')
  assert.ok(!page.includes(String.raw`/^([01]\\d|2[0-3]):[0-5]\\d$/`))
  assert.match(picker, /Array\.from\(\{ length: 24 \}/)
  assert.match(picker, /Array\.from\(\{ length: 60 \}/)
  assert.match(picker, /type="time"/)
})

test('envio de mídia do computador aparece logo após fotos Shopee, antes da persona', async () => {
  const page = await source('pages/PostsPage.tsx')
  const shopee = page.indexOf('Usar fotos dos produtos Shopee na publicação')
  const media = page.indexOf('Mídia (imagem/vídeo)')
  const persona = page.indexOf('label="Persona da IA"')
  assert.ok(shopee >= 0 && shopee < media && media < persona,
    'Seletor de arquivo deve ficar diretamente abaixo das fotos Shopee e acima da IA')
  assert.equal(page.split('ref={fileInputRef}').length - 1, 1,
    'O mesmo input de mídia deve continuar único, sem duplicação de comportamento')
})
