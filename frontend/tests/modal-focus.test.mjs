import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

test('modal usa diálogo nativo fora do conteúdo animado', () => {
  const code = ts.transpileModule(readFileSync(new URL('../src/components/ui/Modal.tsx', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText
  const exports = {}
  let effect
  let closed = 0
  let prevented = false
  let focusRestored = false
  const document = { body: {}, activeElement: { isConnected: true, focus() { focusRestored = true } } }
  const dialog = { open: false, showModal() { this.open = true }, close() { this.open = false } }
  const jsx = (type, props) => ({ type, props })
  runInNewContext(code, { exports, document, require(name) {
    if (name === 'react') return { useRef: () => ({ current: dialog }), useEffect(callback) { effect = callback }, useId: () => 'modal-title' }
    if (name === 'react-dom') return { createPortal: (children, container) => ({ children, container }) }
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx }
    return new Proxy({}, { get: (_, key) => key })
  } })
  const view = exports.Modal({ open: true, onClose: () => { closed++ }, title: 'Editar usuário' })
  assert.equal(view.container, document.body, 'modal precisa escapar do conteúdo animado')
  assert.equal(view.children.type, 'dialog')
  assert.equal(view.children.props['aria-labelledby'], 'modal-title')
  const cleanup = effect()
  assert.equal(dialog.open, true)
  view.children.props.onCancel({ preventDefault() { prevented = true } })
  assert.equal(closed, 1)
  assert.equal(prevented, true)
  cleanup()
  assert.equal(dialog.open, false)
  assert.equal(focusRestored, true)
})
