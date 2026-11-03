import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const source = (path) => readFile(new URL(`../src/${path}`, import.meta.url), 'utf8')

test('edição futura é isolada no detalhe e não altera o criador de posts', async () => {
  const modal = await source('components/posts/PostDetailsModal.tsx')
  const api = await source('api/posts.ts')
  const editor = await source('components/posts/FutureRevisionEditor.tsx')
  assert.match(modal, /details\.scheduled && !details\.publish_immediately/)
  assert.match(modal, /FutureRevisionEditor/)
  assert.match(api, /future-revisions\/latest/)
  assert.match(api, /updateFuture/)
  assert.match(editor, /postsApi\.updateFuture/)
  assert.match(editor, /post\.products\.map\(\(product\) => product\.id\)/)
  assert.doesNotMatch(editor, /postsApi\.createBatch|postsApi\.publishNow|uploadMedia|deleteMedia/)
})

test('orientações de imutabilidade, corte e preservação de mídia aparecem no editor', async () => {
  const editor = await source('components/posts/FutureRevisionEditor.tsx')
  assert.match(editor, /30 minutos/)
  assert.match(editor, /publicados permanecem imutáveis/)
  assert.match(editor, /fotos, vídeos, produto e horários atuais são preservados/)
  assert.match(editor, /getFutureRevision/)
})
