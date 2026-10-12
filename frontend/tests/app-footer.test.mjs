import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = (path) => readFileSync(new URL(path, import.meta.url), 'utf8')

test('footer apresenta os links institucionais e a versão do produto', () => {
  const footer = source('../src/components/layout/AppFooter.tsx')

  assert.match(footer, /APP_VERSION/)
  assert.match(footer, /to="\/privacidade"/)
  assert.match(footer, /to="\/termos"/)
  assert.match(footer, /Raffa Studio Produções/)
})

test('login e painel usam o mesmo rodapé em seus contextos corretos', () => {
  const login = source('../src/pages/LoginPage.tsx')
  const panel = source('../src/pages/PanelPage.tsx')

  assert.match(login, /<AppFooter variant="login" \/>/)
  assert.match(panel, /<AppFooter variant="app" \/>/)
})

test('versão exibida vem do arquivo VERSION no build', () => {
  const viteConfig = source('../vite.config.ts')

  assert.match(viteConfig, /readFileSync\(path\.resolve\(__dirname, '\.\.\/VERSION'\)/)
  assert.match(viteConfig, /__APP_VERSION__/)
})
