import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

// Node 20 do CI não importa .ts: transpila e executa num contexto isolado.
const transpiled = ts.transpileModule(
  readFileSync(new URL('../src/lib/tiktokSharing.ts', import.meta.url), 'utf8'),
  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } },
).outputText
const mod = { exports: {} }
vm.runInNewContext(transpiled, { module: mod, exports: mod.exports })
const {
  emptyTikTokChoice, updateTikTokChoice, tiktokBlockReason, toTikTokPayload, declarationKind,
  privacyOptionDisabledReason, brandContentDisabledReason, commercialLabelNotice, interactionDisabled,
  COMMERCIAL_REQUIRED_HINT, BRANDED_PRIVATE_HINT,
} = mod.exports

const creator = {
  creator_nickname: 'Loja da Ana', creator_username: 'lojadaana', creator_avatar_url: '',
  privacy_level_options: ['FOLLOWER_OF_CREATOR', 'MUTUAL_FOLLOW_FRIENDS', 'SELF_ONLY'],
  comment_disabled: false, duet_disabled: true, stitch_disabled: true,
  max_video_post_duration_sec: 60, can_post: true, cannot_post_reason: null,
}
const ready = (patch = {}) => updateTikTokChoice(emptyTikTokChoice(), { privacy: 'MUTUAL_FOLLOW_FRIENDS', ...patch })

test('privacidade começa sem valor e publicar exige escolher', () => {
  const choice = emptyTikTokChoice()
  assert.equal(choice.privacy, '')
  assert.match(tiktokBlockReason(choice, creator), /Escolha quem pode ver/)
  assert.equal(tiktokBlockReason(ready(), creator), null)
})

test('interações desmarcadas por padrão e desabilitadas quando o criador desligou', () => {
  const choice = emptyTikTokChoice()
  assert.equal(choice.allowComment || choice.allowDuet || choice.allowStitch, false)
  assert.equal(interactionDisabled(creator, 'comment'), false)
  assert.equal(interactionDisabled(creator, 'duet'), true)
  assert.equal(interactionDisabled(undefined, 'comment'), true)
  const payload = toTikTokPayload(ready())
  assert.equal(payload.allow_comment, false)
  assert.equal(payload.allow_duet, false)
})

test('divulgação comercial: desligada por padrão e botão bloqueado se ligada sem opção', () => {
  assert.equal(emptyTikTokChoice().commercial, false)
  const on = ready({ commercial: true })
  assert.equal(tiktokBlockReason(on, creator), COMMERCIAL_REQUIRED_HINT)
  assert.equal(tiktokBlockReason(updateTikTokChoice(on, { brandOrganic: true }), creator), null)
  // desligar limpa as opções marcadas
  const off = updateTikTokChoice(updateTikTokChoice(on, { brandContent: true }), { commercial: false })
  assert.equal(off.brandContent, false)
})

test('conteúdo de marca não pode ser privado (bloqueio nos dois sentidos)', () => {
  const branded = ready({ commercial: true, brandContent: true })
  assert.equal(privacyOptionDisabledReason(branded, 'SELF_ONLY'), BRANDED_PRIVATE_HINT)
  assert.equal(privacyOptionDisabledReason(branded, 'MUTUAL_FOLLOW_FRIENDS'), null)
  const privateChoice = ready({ privacy: 'SELF_ONLY', commercial: true })
  assert.equal(brandContentDisabledReason(privateChoice), BRANDED_PRIVATE_HINT)
  assert.equal(tiktokBlockReason({ ...privateChoice, brandContent: true }, creator), BRANDED_PRIVATE_HINT)
})

test('rótulo e declaração seguem a seleção', () => {
  assert.equal(declarationKind(ready()), 'music')
  assert.match(commercialLabelNotice(ready({ commercial: true, brandOrganic: true })), /Conteúdo promocional/)
  const both = ready({ commercial: true, brandOrganic: true, brandContent: true })
  assert.match(commercialLabelNotice(both), /Parceria paga/)
  assert.equal(declarationKind(both), 'branded')
})

test('conta que não pode postar, opção indisponível e vídeo longo bloqueiam', () => {
  assert.match(tiktokBlockReason(ready(), { ...creator, can_post: false, cannot_post_reason: 'limite diário' }), /limite diário/)
  assert.match(tiktokBlockReason(ready({ privacy: 'PUBLIC_TO_EVERYONE' }), creator), /não está disponível/)
  assert.match(tiktokBlockReason(ready(), creator, { videoDurationSec: 61 }), /até 60 s/)
  assert.match(tiktokBlockReason(ready(), undefined, { loading: true }), /Consultando/)
})

test('modo rascunho não envia privacidade nem divulgação, só o consentimento', () => {
  const draft = updateTikTokChoice(ready({ commercial: true, brandContent: true }), { mode: 'draft' })
  assert.equal(tiktokBlockReason(draft, creator), null)
  assert.deepEqual({ ...toTikTokPayload(draft) }, { mode: 'draft', consent: true })
})

test('payload direto carrega exatamente a escolha e o consentimento', () => {
  const payload = toTikTokPayload(ready({ allowComment: true, commercial: true, brandOrganic: true, isAigc: true }))
  assert.deepEqual({ ...payload }, {
    mode: 'direct', privacy_level: 'MUTUAL_FOLLOW_FRIENDS', allow_comment: true, allow_duet: false,
    allow_stitch: false, commercial_content: true, brand_organic: true, brand_content: false,
    is_aigc: true, consent: true,
  })
})

test('compositor e campanha só liberam o envio com as regras do TikTok', () => {
  const composer = readFileSync(new URL('../src/components/posts/PostComposer.tsx', import.meta.url), 'utf8')
  assert.match(composer, /!tiktokBlock &&/)
  assert.match(composer, /<TikTokDeclaration choice=\{tiktokChoice\} \/>/)
  assert.doesNotMatch(composer, /tiktokChoice,[^\n]*useAutosavedDraft|useAutosavedDraft\([^)]*tiktokChoice/)
  const planner = readFileSync(new URL('../src/components/campaigns/CampaignPlanner.tsx', import.meta.url), 'utf8')
  assert.match(planner, /tiktok: toTikTokPayload\(tiktokChoice\)/)
  assert.match(planner, /!draft\.networks\.length \|\| tiktokBlock/)
  const panel = readFileSync(new URL('../src/components/posts/TikTokPublishPanel.tsx', import.meta.url), 'utf8')
  assert.match(panel, /href=\{MUSIC_USAGE_URL\}/)
  assert.match(panel, /href=\{BRANDED_CONTENT_POLICY_URL\}/)
  assert.equal(mod.exports.MUSIC_USAGE_URL, 'https://www.tiktok.com/legal/page/global/music-usage-confirmation/en')
  assert.equal(mod.exports.BRANDED_CONTENT_POLICY_URL, 'https://www.tiktok.com/legal/page/global/bc-policy/en')
  assert.match(panel, /<option value="" disabled>Selecione<\/option>/)
})
