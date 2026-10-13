import assert from 'node:assert/strict'
import test from 'node:test'

const { NETWORK_RULES } = await import('../src/lib/networkLimits.ts')
const { adaptMedia, describeKept, filterPicked, pickLimits, pickNotice } = await import('../src/lib/mediaAdapt.ts')

const MB = 1024 * 1024
const item = (name, kind, size = 1024) => ({ name, size, kind })
const img = (n) => item(`f${n}.jpg`, 'image')
const names = (list) => list.map((m) => m.name)

test('X recebe só a 1ª foto (carrossel não é entregue) e informa o resto', () => {
  const { kept, dropped } = adaptMedia(NETWORK_RULES.x, [1, 2, 3, 4, 5].map(img))
  assert.deepEqual(names(kept), ['f1.jpg'])
  assert.deepEqual(names(dropped.map((d) => d.item)), ['f2.jpg', 'f3.jpg', 'f4.jpg', 'f5.jpg'])
})

test('Facebook: fotos têm prioridade e o vídeo/GIF ficam de fora, na ordem do usuário', () => {
  const list = [img(1), item('v.mp4', 'video'), img(2), item('a.gif', 'gif')]
  const { kept, dropped } = adaptMedia(NETWORK_RULES.facebook, list)
  assert.deepEqual(names(kept), ['f1.jpg', 'f2.jpg'])
  assert.equal(dropped.length, 2)
  assert.ok(dropped.every((d) => d.reason.length > 0))
  assert.equal(list.length, 4)
})

test('Facebook só com vídeos manda o 1º vídeo', () => {
  const { kept } = adaptMedia(NETWORK_RULES.facebook, [item('a.mp4', 'video'), item('b.mp4', 'video')])
  assert.deepEqual(names(kept), ['a.mp4'])
})

test('TikTok descarta fotos e fica com o vídeo', () => {
  const { kept, dropped } = adaptMedia(NETWORK_RULES.tiktok, [img(1), item('v.mp4', 'video')])
  assert.deepEqual(names(kept), ['v.mp4'])
  assert.equal(dropped.length, 1)
})

test('Instagram trunca em 10 e descarta formato e tamanho inválidos', () => {
  const list = [...Array.from({ length: 11 }, (_, i) => img(i + 1)), item('x.webp', 'image'), item('g.jpg', 'image', 9 * MB)]
  const { kept, dropped } = adaptMedia(NETWORK_RULES.instagram, list)
  assert.equal(kept.length, 10)
  assert.equal(kept[9].name, 'f10.jpg')
  assert.equal(dropped.length, 3)
})

test('describeKept resume o que a rede recebe', () => {
  assert.equal(describeKept([img(1), img(2), img(3)]), '3 fotos')
  assert.equal(describeKept([img(1)]), '1 foto')
  assert.equal(describeKept([img(1), item('v.mp4', 'video')]), '1 foto e 1 vídeo')
  assert.equal(describeKept([item('a.gif', 'gif')]), '1 GIF')
})

test('pickLimits usa o máximo absoluto por tipo entre as redes marcadas', () => {
  const l = pickLimits([NETWORK_RULES.threads, NETWORK_RULES.x, NETWORK_RULES.tiktok])
  assert.equal(l.max.image, 20)
  assert.equal(l.max.video, 20)
  const t = pickLimits([NETWORK_RULES.tiktok])
  assert.equal(t.max.image, 0)
  assert.equal(t.max.video, 1)
  assert.deepEqual(t.exts, ['mp4'])
  const x = pickLimits([NETWORK_RULES.x])
  assert.equal(x.max.image, 1)
  assert.equal(x.max.video, 0)
  assert.ok(!x.exts.includes('mp4'))
})

test('pickLimits sem redes não limita', () => {
  const l = pickLimits([])
  assert.equal(l.max.image, Infinity)
  assert.ok(l.exts.includes('jpg') && l.exts.includes('mp4'))
})

test('filterPicked ignora formato que nenhuma rede aceita e corta o excesso por tipo', () => {
  const l = pickLimits([NETWORK_RULES.tiktok])
  const r = filterPicked([{ name: 'a.jpg' }, { name: 'b.mp4' }, { name: 'c.mp4' }, { name: 'd.pdf' }], [], l)
  assert.deepEqual(r.accepted.map((f) => f.name), ['b.mp4'])
  assert.equal(r.ignored, 2)
  assert.equal(r.overLimit, 1)
})

test('filterPicked conta o que já está na lista', () => {
  const l = pickLimits([NETWORK_RULES.x])
  const r = filterPicked([{ name: 'b.jpg' }], ['image'], l)
  assert.equal(r.accepted.length, 0)
  assert.equal(r.overLimit, 1)
})

test('pickNotice gera uma linha curta em português', () => {
  assert.equal(pickNotice({ ignored: 0, overLimit: 0 }), null)
  assert.equal(
    pickNotice({ ignored: 2, overLimit: 0 }),
    '2 arquivos ignorados: formato não aceito por nenhuma rede selecionada',
  )
  assert.match(pickNotice({ ignored: 1, overLimit: 3 }), /1 arquivo ignorado.*3 arquivos acima do limite/)
})
