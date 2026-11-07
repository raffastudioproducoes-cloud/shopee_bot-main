import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const source = (path) => readFile(new URL(`../src/${path}`, import.meta.url), 'utf8')

test('compositor só oferece agora e recorrente, com produto individual', async () => {
  const page = await source('components/posts/PostComposer.tsx')
  const picker = await source('components/posts/PostProductPicker.tsx')
  assert.match(page, /value: "now", label: "Agora"/)
  assert.match(page, /value: "cron", label: "Recorrente"/)
  assert.doesNotMatch(page, /value: "date", label: "Agendar"/)
  assert.match(picker, /type="radio"/)
  assert.doesNotMatch(picker, /onToggleList/)
})

test('validação de hora usa dígitos reais e controle 24h', async () => {
  const page = await source('components/posts/PostComposer.tsx')
  const picker = await source('components/posts/PostTimePicker.tsx')
  assert.ok(page.includes(String.raw`/^([01]\d|2[0-3]):[0-5]\d$/`),
    'Expressão HH:MM deve usar classe de dígitos, não barras literais')
  assert.ok(!page.includes(String.raw`/^([01]\\d|2[0-3]):[0-5]\\d$/`))
  assert.match(picker, /Array\.from\(\{ length: 24 \}/)
  assert.match(picker, /Array\.from\(\{ length: 60 \}/)
  assert.match(picker, /type="time"/)
})

test('envio de mídia do computador aparece logo após fotos Shopee, antes da persona', async () => {
  const page = await source('components/posts/PostComposer.tsx')
  const shopee = page.indexOf('Usar fotos dos produtos Shopee na publicação')
  const media = page.indexOf('Mídia (imagem/vídeo)')
  const ai = page.indexOf('<AiCopyControls')
  const persona = await source('components/posts/AiCopyControls.tsx')
  assert.ok(shopee >= 0 && shopee < media && media < ai,
    'Seletor de arquivo deve ficar abaixo das fotos Shopee e antes dos controles de IA')
  assert.match(persona, /label="Persona da IA"/)
  assert.equal(page.split('ref={fileInputRef}').length - 1, 1,
    'O mesmo input de mídia deve continuar único, sem duplicação de comportamento')
})

test('IA cria descrições por rede e sinaliza ajustes de limites', async () => {
  const limits = await source('lib/networkLimits.ts')
  const page = await source('components/posts/PostComposer.tsx')
  const ai = await source('components/posts/AiCopyControls.tsx')
  const tabs = await source('components/posts/TextVariantTabs.tsx')
  assert.match(limits, /key: network,/)
  assert.match(limits, /networks: \[network\],/)
  assert.match(page, /const adjusted = \(res\.variants \?\? \[\]\)\.filter/)
  assert.match(page, /disabled=\{selectedProductIds\.length === 0 \|\| activeNetworks\.length === 0\}/)
  assert.match(page, /isPending=\{generateMutation\.isPending\}/)
  assert.match(ai, /disabled=\{disabled \|\| isPending\}/)
  assert.match(tabs, /Cada rede tem sua própria descrição/)
})

test('resumo de mídia explicita exclusão e publicação sem arquivo', async () => {
  const summary = await source('components/posts/MediaSummary.tsx')
  assert.match(summary, /rede excluída deste envio/)
  assert.match(summary, /publicará sem imagem\/vídeo/)
  assert.match(summary, /de \$\{total\} mídias/)
})


test('agendador indisponível bloqueia envio antes de upload e preserva rascunho', async () => {
  const page = await source('pages/CreatePostPage.tsx')
  const composer = await source('components/posts/PostComposer.tsx')
  const client = await source('api/posts.ts')
  assert.match(client, /schedulerStatus\(\)/)
  assert.match(client, /\/posts\/scheduler-status/)
  assert.ok(page.indexOf('await postsApi.schedulerStatus()') < page.indexOf('for (const file of data.files)'))
  assert.match(composer, /schedulerAvailable &&/)
  assert.match(composer, /role="alert"/)
  assert.match(composer, /Seu rascunho permanece salvo|seu rascunho permanece salvo|seu rascunho foi preservado/i)
})


test('IDs visíveis e agrupamento nunca funde posts independentes pelo texto ou horário', async () => {
  const page = await source('pages/PostsPage.tsx')
  const details = await source('components/posts/PostDetailsModal.tsx')
  assert.match(page, /post-list-id/)
  assert.match(page, /#\{post\.id\}/)
  assert.match(details, /Post #\{details\.id\}/)
  assert.match(page, /if \(!post\.group_id\) continue/)
  assert.doesNotMatch(page, /GROUP_WINDOW_MS|head\.text === p\.text/)
})

test('falha após criar post não provoca reenvio automático da criação', async () => {
  const page = await source('pages/CreatePostPage.tsx')
  assert.match(page, /Promise\.allSettled\(result\.created\.map/)
  assert.match(page, /postId: created\.post_id/)
  assert.match(page, /Post criado, mas o disparo imediato não foi confirmado/)
  assert.match(page, /const pendingDispatch = list\.some/)
})
