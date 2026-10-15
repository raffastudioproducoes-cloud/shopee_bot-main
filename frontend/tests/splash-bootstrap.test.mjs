import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8')
const mainSource = readFileSync(new URL('../src/main.tsx', import.meta.url), 'utf8')

test('#site-splash é um status acessível ocupado com rótulo válido', () => {
  const tag = html.match(/<div id="site-splash"[^>]*>/)?.[0] ?? ''
  assert.match(tag, /role="status"/)
  assert.match(tag, /aria-busy="true"/)
  assert.match(tag, /aria-label="Carregando Auto Orbital"/)
})

test('HTML tem timeout de segurança, handlers de erro, botão recarregar e noscript', () => {
  assert.match(html, /15000/)
  assert.match(html, /window\.addEventListener\('error'/)
  assert.match(html, /unhandledrejection/)
  assert.match(html, /location\.reload\(\)/)
  assert.match(html, /<noscript>/)
  assert.match(html, /__appReady/)
})

function boot({ reduced = false, loadFails = false } = {}) {
  assert.doesNotMatch(mainSource, /flushSync/)
  const code = ts.transpileModule(mainSource.replaceAll('import.meta.env.PROD', 'false'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, esModuleInterop: true } }).outputText
  const log = []
  const timers = []
  const frames = []
  const splash = { classList: { add: (c) => log.push(`class:${c}`) }, remove: () => log.push('remove'), setAttribute() {} }
  const win = {
    __appReady: false,
    setTimeout: (cb, ms) => timers.push({ cb, ms }),
    requestAnimationFrame: (cb) => frames.push(cb),
    matchMedia: () => ({ matches: reduced }),
  }
  const deps = {
    react: { createElement: () => ({}), StrictMode: 'strict' },
    'react-dom/client': { createRoot: () => ({ render: () => log.push('render') }) },
    '@tanstack/react-router': { RouterProvider() {} },
    '@tanstack/react-query': { MutationCache: class {}, QueryClient: class {}, QueryClientProvider() {} },
    './router': { router: { load: () => { log.push('load'); return loadFails ? Promise.reject(new Error('x')) : Promise.resolve() } } },
    './lib/api': { ApiError: class extends Error {} },
    './stores/toastStore': {}, './components/ui/Toaster': {}, './appMeta': {}, './index.css': {},
  }
  runInNewContext(code, {
    exports: {}, require: (n) => { assert.ok(n in deps, n); return deps[n] },
    document: { getElementById: (id) => id === 'site-splash' ? splash : {} },
    window: win, navigator: {},
  })
  return { log, timers, frames, win }
}
const flush = () => new Promise((r) => setImmediate(r))

test('splash só sai após router carregado e dois requestAnimationFrame, com fade de 300ms', async () => {
  const { log, timers, frames, win } = boot()
  await flush()
  assert.ok(log.includes('render') && log.includes('load'))
  assert.equal(log.includes('class:is-leaving'), false, 'saiu antes do primeiro paint')
  assert.equal(frames.length, 1)
  frames.shift()()
  assert.equal(log.includes('class:is-leaving'), false, 'saiu após só um frame')
  frames.shift()()
  assert.equal(log.includes('class:is-leaving'), true)
  assert.equal(win.__appReady, true)
  const fade = timers.find((t) => t.ms === 300)
  assert.ok(fade, 'fade de ~300ms ausente')
  fade.cb()
  assert.ok(log.includes('remove'))
})

test('prefers-reduced-motion remove o splash sem fade', async () => {
  const { log, frames } = boot({ reduced: true })
  await flush(); frames.shift()(); frames.shift()()
  assert.ok(log.includes('remove'))
  assert.equal(log.includes('class:is-leaving'), false)
})

test('falha em router.load ainda dispensa o splash', async () => {
  const { log, frames } = boot({ loadFails: true })
  await flush(); frames.shift()(); frames.shift()()
  assert.ok(log.includes('class:is-leaving'))
})
