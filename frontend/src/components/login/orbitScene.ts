// @ts-nocheck — cena three.js portada da prévia aprovada; a tipagem fica nas bordas (função exportada).
// Animação "Do caos à órbita" da tela de login: posts bagunçados → grade organizada → logo.
// Determinística no tempo (frame(t)); pausa fora da tela/aba; libera a GPU ao desmontar.
import * as THREE from 'three'

export interface OrbitSceneElements {
  stage: HTMLElement; canvas: HTMLCanvasElement; word: HTMLElement; flash: HTMLElement
  end: HTMLElement; mark: HTMLElement; name: HTMLElement; tag: HTMLElement; sub: HTMLElement
}

/* ---------------- linha do tempo (segundos) ---------------- */
const LOOP = 15.0
const T = { burst: 0.7, chaosEnd: 4.7, orgEnd: 6.9, holdEnd: 9.3, sinkEnd: 10.5, endOut: 14.4 }
const WORDS = [
  { a: 0.55, b: 1.20, text: 'Copia.', rot: -5, x: -8, y: -6, size: 1.0, color: '#ffffff' },
  { a: 1.20, b: 1.85, text: 'Cola.', rot: 4, x: 9, y: 5, size: 1.05, color: '#1FD3FD' },
  { a: 1.85, b: 2.50, text: 'Posta.', rot: -3, x: -5, y: 7, size: 1.1, color: '#ffffff' },
  { a: 2.50, b: 3.25, text: 'Repete.', rot: 5, x: 6, y: -4, size: 1.15, color: '#b784f8' },
  { a: 3.25, b: 3.95, text: 'De novo?', rot: -2, x: 0, y: 0, size: 1.0, color: '#ffffff' },
  { a: 3.95, b: 4.95, text: 'Chega.', rot: 0, x: 0, y: 0, size: 1.32, color: '#ffffff', glow: '#1FD3FD' },
  { a: 5.45, b: 6.75, text: 'Um lugar\nsó.', rot: 0, x: 0, y: 0, size: 0.95, color: '#ffffff', calm: true },
  { a: 7.75, b: 9.2, text: 'Cada post\nno seu horário.', rot: 0, x: 0, y: 0, size: 0.66, color: '#ffffff', calm: true, glow: '#5f8dff' },
]

/* ---------------- utilidades determinísticas ---------------- */
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v))
const lerp = (a, b, t) => a + (b - a) * t
const ss = (t) => { t = clamp(t); return t * t * (3 - 2 * t) }
const easeOutExpo = (t) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * clamp(t)))
const easeInCubic = (t) => { t = clamp(t); return t * t * t }
const easeInOut = (t) => { t = clamp(t); return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2 }
function rng(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296 } }
const hash = (n) => { const x = Math.sin(n * 127.1) * 43758.5453; return x - Math.floor(x) }


/** Inicia a cena e devolve a função que para tudo e libera os recursos. Lança se não houver WebGL. */
export function startOrbitScene(els: OrbitSceneElements): () => void {
  const { stage, canvas, word: elK, flash: elFlash, end: elEnd, mark: elMark, name: elWord, tag: elTag, sub: elSub } = els
  /* ---------------- cena ---------------- */
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, preserveDrawingBuffer: true, powerPreference: 'low-power' })
  renderer.autoClear = false
  renderer.setClearColor(0x04070f, 1)
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100)
  const BG = new THREE.Color(0x04070f)

  // véu que apaga o quadro anterior aos poucos: no caos deixa rastro (borrão de movimento); organizado fica nítido
  const fadeScene = new THREE.Scene()
  const fadeCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1)
  const fadeMat = new THREE.MeshBasicMaterial({ color: BG, transparent: true, opacity: 1, depthTest: false, depthWrite: false })
  fadeScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), fadeMat))

  /* ---------------- texturas de "post" ---------------- */
  const NETS = [
    { name: 'threads', a: '#f4f4f6', b: '#d9dbe4', ink: '#0b0d14', accent: '#0b0d14' },
    { name: 'instagram', a: '#ff7a3d', b: '#d62f8f', ink: '#ffffff', accent: '#ffd36b' },
    { name: 'facebook', a: '#2f6bff', b: '#1b3fb8', ink: '#ffffff', accent: '#9cc0ff' },
    { name: 'tiktok', a: '#12141c', b: '#1d2030', ink: '#ffffff', accent: '#25f4ee' },
    { name: 'x', a: '#1a1d28', b: '#0c0e16', ink: '#ffffff', accent: '#8aa0c8' },
    { name: 'shopee', a: '#ff6a3a', b: '#ee4d2d', ink: '#ffffff', accent: '#ffe1d6' },
  ]
  function rr(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath() }
  function postTexture(net, variant) {
    const W = 256, H = 336, c = document.createElement('canvas'); c.width = W; c.height = H
    const g = c.getContext('2d')
    g.clearRect(0, 0, W, H)
    rr(g, 6, 6, W - 12, H - 12, 26); g.fillStyle = '#0f1424'; g.fill()
    g.lineWidth = 2; g.strokeStyle = 'rgba(160,190,255,.28)'; g.stroke()
    // cabeçalho: avatar + nome
    g.fillStyle = net.accent; g.beginPath(); g.arc(40, 44, 16, 0, 7); g.fill()
    g.fillStyle = 'rgba(255,255,255,.85)'; rr(g, 66, 32, 96, 10, 5); g.fill()
    g.fillStyle = 'rgba(255,255,255,.35)'; rr(g, 66, 48, 60, 8, 4); g.fill()
    // mídia
    const gr = g.createLinearGradient(20, 76, W - 20, 226); gr.addColorStop(0, net.a); gr.addColorStop(1, net.b)
    rr(g, 20, 76, W - 40, 150, 16); g.fillStyle = gr; g.fill()
    g.fillStyle = 'rgba(255,255,255,.22)'
    if (variant % 3 === 0) { g.beginPath(); g.moveTo(108, 122); g.lineTo(158, 151); g.lineTo(108, 180); g.closePath(); g.fill() }
    else if (variant % 3 === 1) { g.beginPath(); g.moveTo(34, 214); g.lineTo(96, 140); g.lineTo(140, 190); g.lineTo(170, 160); g.lineTo(222, 214); g.closePath(); g.fill(); g.beginPath(); g.arc(186, 112, 14, 0, 7); g.fill() }
    else { rr(g, 44, 102, 168, 16, 8); g.fill(); rr(g, 44, 130, 120, 16, 8); g.fill(); rr(g, 44, 158, 146, 16, 8); g.fill() }
    // legenda
    g.fillStyle = 'rgba(255,255,255,.7)'; rr(g, 20, 244, W - 60, 10, 5); g.fill()
    g.fillStyle = 'rgba(255,255,255,.4)'; rr(g, 20, 262, W - 110, 10, 5); g.fill()
    // rodapé: horário
    g.fillStyle = 'rgba(31,211,253,.9)'; rr(g, 20, 290, 74, 22, 11); g.fill()
    g.fillStyle = 'rgba(255,255,255,.25)'; g.beginPath(); g.arc(W - 34, 301, 9, 0, 7); g.fill(); g.beginPath(); g.arc(W - 60, 301, 9, 0, 7); g.fill()
    const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4
    return tex
  }
  const textures = []
  NETS.forEach((n, i) => { for (let v = 0; v < 3; v++) textures.push(postTexture(n, i + v)) })

  /* ---------------- cards ---------------- */
  const COLS = 8, ROWS = 4, PER = COLS * ROWS, N = PER * 2
  const CW = 1.18, CH = 1.55, GX = 1.42, GY = 1.84
  const geo = new THREE.PlaneGeometry(CW, CH)
  const cards = []
  const r = rng(20261110)
  for (let i = 0; i < N; i++) {
    const layer = i < PER ? 0 : 1, j = i % PER, col = j % COLS, row = Math.floor(j / COLS)
    const mat = new THREE.MeshBasicMaterial({ map: textures[Math.floor(r() * textures.length)], transparent: true, side: THREE.DoubleSide, depthWrite: false })
    const mesh = new THREE.Mesh(geo, mat); scene.add(mesh)
    cards.push({
      mesh, layer, col, row,
      slot: new THREE.Vector3((col - (COLS - 1) / 2) * GX + (layer ? GX / 2 : 0), ((ROWS - 1) / 2 - row) * GY + (layer ? -GY / 2 : 0), layer ? -5.5 : 0),
      base: new THREE.Vector3((r() - .5) * 15, (r() - .5) * 9, -7 + r() * 11),
      amp: new THREE.Vector3(.9 + r() * 1.6, .7 + r() * 1.4, .8 + r() * 1.8),
      f: new THREE.Vector3(2.2 + r() * 4.2, 2.0 + r() * 4.6, 1.6 + r() * 3.4),
      p: new THREE.Vector3(r() * 6.28, r() * 6.28, r() * 6.28),
      spin: new THREE.Vector3((r() - .5) * 9, (r() - .5) * 9, (r() - .5) * 7),
      delay: r() * 0.85, sinkDelay: 0, sw: (r() - .5) * 2,
    })
  }
  cards.forEach((c) => { c.sinkDelay = clamp(1 - c.slot.length() / 9, 0, 1) * 0.45 })

  /* ---------------- poeira de estrelas ---------------- */
  const SN = 520, sp = new Float32Array(SN * 3), sr = rng(7)
  for (let i = 0; i < SN; i++) { sp[i * 3] = (sr() - .5) * 34; sp[i * 3 + 1] = (sr() - .5) * 20; sp[i * 3 + 2] = -14 + sr() * 16 }
  const sgeo = new THREE.BufferGeometry(); sgeo.setAttribute('position', new THREE.BufferAttribute(sp, 3))
  const smat = new THREE.PointsMaterial({ color: 0x9db8ff, size: 0.06, transparent: true, opacity: .7, depthWrite: false })
  const stars = new THREE.Points(sgeo, smat); scene.add(stars)

  /* ---------------- DOM ---------------- */
  let W = 1, H = 1
  function resize() {
    W = Math.max(1, stage.clientWidth); H = Math.max(1, stage.clientHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5)); renderer.setSize(W, H, false)
    camera.aspect = W / H; camera.updateProjectionMatrix()
  }
  resize()

  const q = new THREE.Quaternion(), qI = new THREE.Quaternion(), e = new THREE.Euler(), v = new THREE.Vector3(), v2 = new THREE.Vector3()

  function chaosPos(c, t, out) {
    out.set(
      c.base.x + Math.sin(t * c.f.x + c.p.x) * c.amp.x + Math.sin(t * c.f.y * 2.3 + c.p.z) * .35,
      c.base.y + Math.cos(t * c.f.y + c.p.y) * c.amp.y + Math.sin(t * c.f.x * 2.1 + c.p.x) * .3,
      c.base.z + Math.sin(t * c.f.z + c.p.z) * c.amp.z,
    )
    return out
  }

  function frame(tRaw) {
    const t = ((tRaw % LOOP) + LOOP) % LOOP
    const aspect = W / H
    // a grade precisa caber: afasta a câmera em telas estreitas
    const fit = Math.max(1, 1.62 / aspect)
    const inChaos = t < T.chaosEnd
    const org = ss((t - T.chaosEnd) / (T.orgEnd - T.chaosEnd))        // 0 caos → 1 organizado
    const sink = clamp((t - T.holdEnd) / (T.sinkEnd - T.holdEnd))     // 0 → 1 engolido pelo buraco negro
    const ended = t >= T.sinkEnd

    /* câmera */
    const shake = (1 - org) * (t < T.burst ? 1.6 : 1) * (t > 3.9 && t < 4.7 ? 2.2 : 1)
    const sx = (hash(Math.floor(t * 30) * 1.3) - .5) * .34 * shake, sy = (hash(Math.floor(t * 30) * 2.7 + 9) - .5) * .26 * shake
    const drift = Math.sin(t * .5) * .35 * org
    const push = lerp(0, -1.2, ss((t - T.orgEnd) / (T.holdEnd - T.orgEnd)))          // aproxima devagar na parte organizada
    const zoomIn = easeInCubic(sink) * 3.2
    camera.position.set(sx + drift, sy + Math.sin(t * .37) * .12 * org, (11.4 + push) * fit - zoomIn)
    camera.rotation.set(0, 0, (1 - org) * Math.sin(t * 2.3) * .045 + sx * .12)
    camera.lookAt(drift * .4, 0, -1)
    camera.rotateZ((1 - org) * Math.sin(t * 2.3) * .04)

    /* cards */
    let dim = 1
    for (const w of WORDS) if (w.calm && t > w.a - .1 && t < w.b + .1) dim = lerp(1, .32, Math.min(ss((t - w.a + .1) / .4), ss((w.b + .1 - t) / .35)))
    const burst = easeOutExpo(t / T.burst)
    for (const c of cards) {
      const m = c.mesh
      chaosPos(c, t, v)
      if (t < T.burst) v.multiplyScalar(burst)
      const u = easeInOut((t - T.chaosEnd + 0.35 - c.delay) / 1.45)
      // redemoinho a caminho do lugar
      const sw = Math.sin(Math.PI * u) * 2.4 * c.sw
      v2.copy(c.slot); v2.x += -v.y * 0 + Math.cos(u * 5 + c.p.x) * sw; v2.y += Math.sin(u * 5 + c.p.x) * sw
      v.lerp(v2, u)
      // respiração leve depois de organizado
      if (u >= 1) v.y += Math.sin(t * 1.4 + c.col * .5) * .035
      e.set(t * c.spin.x, t * c.spin.y, t * c.spin.z); q.setFromEuler(e); q.slerp(qI, easeInOut(u * 1.15))
      let scale = (t < T.burst ? burst : 1) * lerp(.82, 1, u)
      let op = (c.layer ? lerp(.9, .34, u) : 1)
      let bright = 1
      // onda de "agendado": acende coluna por coluna
      if (u >= 1 && !c.layer) { const wv = (t - T.orgEnd - .05) * 6 - c.col * .55 - c.row * .22; bright = 1 + Math.exp(-wv * wv * 1.6) * .9 }
      // buraco negro engole
      if (sink > 0) {
        const k = easeInCubic(clamp((sink - c.sinkDelay) / (1 - c.sinkDelay)))
        const ang = k * 5.2 * (c.sw >= 0 ? 1 : -1), rad = v.length() * (1 - k)
        const a0 = Math.atan2(v.y, v.x) + ang
        v.set(Math.cos(a0) * rad, Math.sin(a0) * rad, lerp(v.z, 0, k))
        e.set(0, 0, ang * 1.2); q.setFromEuler(e)
        scale *= 1 - k * .97; op *= 1 - easeInCubic(k)
      }
      m.position.copy(v); m.quaternion.copy(q); m.scale.setScalar(Math.max(.0001, scale))
      m.material.opacity = ended ? 0 : op; m.material.color.setScalar(bright * dim); m.visible = !ended
    }

    /* estrelas: correm no caos, quase paradas depois */
    stars.rotation.z = t * lerp(.5, .02, org) + sink * 1.6
    stars.position.z = Math.sin(t * 3.1) * .8 * (1 - org)
    smat.opacity = ended ? lerp(.7, .35, ss((t - T.sinkEnd) / .8)) : .7

    /* rastro: muito no caos, nenhum quando organiza */
    fadeMat.opacity = t < 0.05 ? 1 : lerp(.2, 1, ss(org * 1.6)) * (sink > 0 && !ended ? lerp(1, .32, ss(sink)) : 1)
    renderer.render(fadeScene, fadeCam); renderer.clearDepth(); renderer.render(scene, camera)

    /* palavras */
    let shown = false
    for (const w of WORDS) {
      if (t < w.a || t >= w.b) continue
      shown = true
      const pin = clamp((t - w.a) / (w.calm ? .5 : .13)), pout = clamp((w.b - t) / (w.calm ? .35 : .1))
      const base = Math.min(W * .19, H * .30) * w.size
      const sc = w.calm ? lerp(.94, 1, easeOutExpo(pin)) * lerp(.98, 1, pout) : lerp(2.3, 1, easeOutExpo(pin)) * lerp(.9, 1, pout)
      const hold = w.calm ? 0 : Math.sin((t - w.a) * 46) * (1 - pin) * 5
      elK.textContent = w.text
      elK.style.fontSize = base + 'px'
      elK.style.color = w.color
      elK.style.opacity = String(Math.min(pin * 1.4, 1) * pout)
      elK.style.filter = `blur(${((1 - pin) * (w.calm ? 10 : 18)).toFixed(2)}px)`
      elK.style.transform = `translate(${w.x * W / 100 + hold}px, ${w.y * H / 100}px) rotate(${w.rot}deg) scale(${sc.toFixed(3)})`
      elK.style.textShadow = w.glow ? `0 0 ${base * .35}px ${w.glow}, 0 ${base * .04}px ${base * .12}px rgba(0,0,0,.6)` : `0 ${base * .04}px ${base * .14}px rgba(0,0,0,.7)`
      elK.style.letterSpacing = w.calm ? `${lerp(.06, -.02, easeOutExpo(pin))}em` : '-.02em'
    }
    if (!shown) elK.style.opacity = '0'

    /* clarões: "Chega." e o nascimento da logo */
    const f1 = Math.exp(-Math.pow((t - 4.02) / .11, 2)) * .55
    const f2 = Math.exp(-Math.pow((t - T.sinkEnd) / .2, 2)) * .9
    const f0 = Math.exp(-Math.pow(t / .16, 2)) * .5
    elFlash.style.opacity = String(Math.min(1, f0 + f1 + f2))

    /* encerramento: logo + nome + frase */
    const te = t - T.sinkEnd
    if (te > -0.05 && t < LOOP) {
      const out = 1 - ss((t - T.endOut) / (LOOP - T.endOut))
      const a = easeOutExpo(te / 1.0)
      elEnd.style.opacity = String(clamp(te / .25) * out)
      const breathe = 1 + Math.sin(te * 1.3) * .012
      elMark.style.transform = `scale(${(lerp(.35, 1, a) * breathe * lerp(.6, 1, out)).toFixed(4)}) rotate(${(lerp(-14, 0, a)).toFixed(2)}deg)`
      elMark.style.filter = `blur(${((1 - a) * 14).toFixed(2)}px) drop-shadow(0 0 ${(H * .05).toFixed(1)}px rgba(70,120,255,.55))`
      const b = easeOutExpo((te - .45) / .9)
      elWord.style.opacity = String(clamp((te - .45) / .5)); elWord.style.transform = `translateY(${((1 - b) * H * .03).toFixed(2)}px)`; elWord.style.filter = `blur(${((1 - b) * 8).toFixed(2)}px)`
      const c2 = easeOutExpo((te - 1.05) / .7)
      const ts = Math.min(W * .058, H * .075)
      elTag.style.fontSize = ts + 'px'; elTag.style.opacity = String(clamp((te - 1.05) / .3)); elTag.style.transform = `scale(${lerp(1.5, 1, c2).toFixed(3)})`; elTag.style.filter = `blur(${((1 - c2) * 10).toFixed(2)}px)`
      elSub.style.fontSize = ts * .38 + 'px'; elSub.style.opacity = String(ss((te - 1.7) / .7))
    } else { elEnd.style.opacity = '0' }
  }


  /* relógio: só anda com a cena visível */
  let raf = 0, running = false, last = 0, clock = 0
  const tick = (now) => { if (!running) return; clock += Math.min(0.1, (now - last) / 1000); last = now; frame(clock); raf = requestAnimationFrame(tick) }
  const play = () => { if (running) return; running = true; last = performance.now(); raf = requestAnimationFrame(tick) }
  const pause = () => { running = false; cancelAnimationFrame(raf) }
  const ro = new ResizeObserver(() => { resize(); if (!running) frame(clock) }); ro.observe(stage)
  let onScreen = true
  const io = new IntersectionObserver((entries) => { onScreen = entries.some((e) => e.isIntersecting); if (onScreen && !document.hidden) play(); else pause() }); io.observe(stage)
  const onVis = () => { if (document.hidden) pause(); else if (onScreen) play() }
  document.addEventListener('visibilitychange', onVis)
  play()
  return () => {
    pause(); ro.disconnect(); io.disconnect(); document.removeEventListener('visibilitychange', onVis)
    geo.dispose(); sgeo.dispose(); smat.dispose(); fadeMat.dispose()
    cards.forEach((c) => c.mesh.material.dispose()); textures.forEach((t) => t.dispose())
    renderer.dispose()
  }
}
