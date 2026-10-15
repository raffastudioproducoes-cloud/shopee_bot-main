import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

test('Button preserva nome acessível e estado pressionado no DOM', () => {
  const exports = {}
  const code = ts.transpileModule(readFileSync(new URL('../src/components/ui/Button.tsx', import.meta.url), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText
  const jsx = (type, props) => ({ type, props })
  runInNewContext(code, { exports, require(name) {
    if (name === 'react') return { useState: value => [value, () => {}] }
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx }
    return {}
  } })
  const tree = exports.Button({ 'aria-label': 'Aumentar zoom do globo', 'aria-pressed': true, children: '+' })
  assert.equal(tree.props['aria-label'], 'Aumentar zoom do globo')
  assert.equal(tree.props['aria-pressed'], true)
})
