import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const { moveItem, trayLimit } = await import('../src/lib/mediaTray.ts')

test('moveItem reordena sem mutar e ignora índices inválidos', () => {
  const a = ['a', 'b', 'c']
  assert.deepEqual(moveItem(a, 0, 2), ['b', 'c', 'a'])
  assert.deepEqual(moveItem(a, 2, 1), ['a', 'c', 'b'])
  assert.deepEqual(a, ['a', 'b', 'c'])
  assert.deepEqual(moveItem(a, 0, 3), a)
  assert.deepEqual(moveItem(a, -1, 1), a)
})

test('trayLimit usa o menor maxMedia das redes que entregam carrossel', () => {
  const rules = [
    { deliveredModes: ['carousel'], maxMedia: 20 },
    { deliveredModes: ['carousel'], maxMedia: 10 },
    { deliveredModes: ['single_image'], maxMedia: 1 },
    { deliveredModes: ['carousel'] },
  ]
  assert.equal(trayLimit(rules), 10)
  assert.equal(trayLimit([rules[2]]), undefined)
  assert.equal(trayLimit([]), undefined)
})

test('PostComposer mantém bandeja e CreatePostPage sobe arquivos na ordem', () => {
  const composer = readFileSync(new URL('../src/components/posts/PostComposer.tsx', import.meta.url), 'utf8')
  const page = readFileSync(new URL('../src/pages/CreatePostPage.tsx', import.meta.url), 'utf8')
  assert.match(composer, /<MediaTray/)
  assert.match(composer, /moveItem\(prev, from, to\)/)
  assert.match(page, /for \(const file of data\.files\) draftMedia\.push\(await postsApi\.uploadDraftMedia\(file\)\)/)
})
