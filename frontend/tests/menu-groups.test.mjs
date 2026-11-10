import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const src = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8')

test('menu lateral é agrupado por assunto, mantendo a ordem dos itens e o item admin separado', () => {
  const panel = src('pages/PanelPage.tsx')
  const groups = [...panel.matchAll(/value: '([^']+)'.*?group: '([^']+)'/g)].map((m) => [m[1], m[2]])
  assert.deepEqual(groups.map(([v]) => v), ['/app', '/analytics', '/products', '/lists', '/posts', '/posts/criar', '/automacao-posts', '/credentials', '/profiles', '/settings', '/ajuda', '/admin'])
  assert.deepEqual([...new Set(groups.map(([, g]) => g))], ['Visão geral', 'Catálogo', 'Publicação', 'Conta', 'Administração'])
  // Dashboard e Análises continuam no topo (pedido de Rafa)
  assert.deepEqual(groups.slice(0, 2).map(([v]) => v), ['/app', '/analytics'])
})

test('o separador de grupo é acessível e vira título no menu do celular', () => {
  const rail = src('components/ui/SideRail.tsx')
  assert.match(rail, /role="separator" aria-label=\{it\.group\} data-label=\{it\.group\} className="app-rail-sep"/)
  const css = src('index.css')
  assert.match(css, /\.app-rail-sep::before \{ content: attr\(data-label\)/)
  assert.match(css, /\.app-rail \{ overflow-y: auto;[^}]*position: sticky/)
})
