import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import postcss from 'postcss'

test('variantes de página reservam espaço e limitam largura no mobile', () => {
  const css = postcss.parse(readFileSync(new URL('../src/index.css', import.meta.url), 'utf8'))
  const styles = new Map()
  css.walkRules(rule => {
    for (const selector of rule.selector.split(',').map(value => value.trim())) {
      const declarations = styles.get(selector) ?? {}
      rule.walkDecls(declaration => { declarations[declaration.prop] = declaration.value })
      styles.set(selector, declarations)
    }
  })
  assert.equal(styles.get('.page-skeleton')?.display, 'flex')
  assert.equal(styles.get('.page-skeleton-grid')?.display, 'grid')
  assert.equal(styles.get('.page-skeleton .skeleton')?.['max-width'], '100%')
  for (const variant of ['list', 'form', 'table']) {
    assert.ok(styles.get(`.page-skeleton-${variant}`), `layout ausente: ${variant}`)
  }
})
