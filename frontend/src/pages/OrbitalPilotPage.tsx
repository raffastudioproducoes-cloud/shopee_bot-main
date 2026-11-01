import { useEffect, useRef, useState, type CSSProperties } from "react"
import { ArrowLeft, Pause, Play, RotateCcw } from "lucide-react"
import "./OrbitalPilotPage.css"

/**
 * Estudo V3: tudo é gerado por Canvas 2D, tipografia e DOM/CSS.
 * Nenhuma imagem, vídeo, shader baixado ou áudio. Previa isolada.
 * A marca no último beat é uma INTERPRETAÇÃO VETORIAL, não o master oficial.
 */
const DURATION_MS = 10_000
const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x))
const ease = (a: number, b: number, x: number) => {
  const t = clamp((x - a) / (b - a))
  return t * t * (3 - 2 * t)
}
const lerp = (a: number, b: number, t: number) => a + (b - a) * t
const fract = (n: number) => n - Math.floor(n)
const random = (seed: number) => fract(Math.sin(seed * 127.1 + 42.23) * 43758.5453)

const chapters = [
  { until: .24, title: "O primeiro produto", detail: "Uma oportunidade vira muitas tarefas." },
  { until: .37, title: "A sobrecarga", detail: "Abas e horários disputam a sua atenção." },
  { until: .43, title: "A pausa", detail: "Existe outro caminho." },
  { until: .61, title: "A transformação", detail: "Cada produto encontra seu lugar na órbita." },
  { until: .76, title: "O painel", detail: "Produtos, posts e destinos em um único fluxo." },
  { until: 1.01, title: "A identidade", detail: "Uma visão de organização e automação para afiliados." },
]
const sheets = [
  { action: "COPIAR", platform: "Threads", category: "01" },
  { action: "EDITAR TEXTO", platform: "Instagram", category: "02" },
  { action: "ESCOLHER REDE", platform: "Facebook", category: "03" },
  { action: "AGENDAR", platform: "TikTok", category: "04" },
  { action: "PUBLICAR", platform: "X", category: "05" },
  { action: "CONFERIR", platform: "Threads", category: "06" },
  { action: "REPETIR", platform: "Instagram", category: "07" },
  { action: "NOVA ABA", platform: "Facebook", category: "08" },
]
const scatter = [
  [-355, -130], [310, -175], [-255, 145], [338, 145],
  [40, -212], [-42, 210], [-390, 30], [400, 10],
]

function drawSpace(canvas: HTMLCanvasElement, progress: number) {
  const ctx = canvas.getContext("2d", { alpha: true })
  if (!ctx) return
  const bounds = canvas.getBoundingClientRect()
  if (!bounds.width || !bounds.height) return
  const dpr = Math.min(window.devicePixelRatio || 1, 1.5)
  const width = Math.max(1, Math.round(bounds.width * dpr))
  const height = Math.max(1, Math.round(bounds.height * dpr))
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width
    canvas.height = height
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  const w = bounds.width, h = bounds.height
  ctx.clearRect(0, 0, w, h)

  // Estrelas procedurais: profundidade, parallax e riscos discretos.
  for (let i = 0; i < 95; i++) {
    const depth = .25 + random(i + 311) * .75
    const x = (random(i * 7 + 21) * w + progress * (40 + 70 * depth)) % w
    const y = (random(i * 3 + 189) * h + Math.sin(progress * 5 + i) * 5 * depth)
    const r = .35 + depth * 1.5
    ctx.fillStyle = "rgba(115,207,255," + (.1 + depth * .35).toFixed(3) + ")"
    ctx.beginPath()
    ctx.arc(x, y, r, 0, Math.PI * 2)
    ctx.fill()
  }
  const reveal = ease(.405, .55, progress) * (1 - ease(.63, .72, progress) * .62)
  const comeback = ease(.77, .9, progress)
  const alpha = clamp(reveal + comeback * .92)
  if (alpha < .005) return

  ctx.save()
  ctx.translate(w * .5, h * .52)
  const scale = Math.min(w / 950, h / 590) * lerp(.68, 1.18, ease(.43, .75, progress))
  ctx.scale(scale, scale)
  ctx.rotate(lerp(-.2, .18, ease(.44, .72, progress)))
  ctx.globalAlpha = alpha

  // Luz de acreção e lente gravitacional: círculos, elipses e composições aditivas.
  const aura = ctx.createRadialGradient(0, 0, 52, 0, 0, 280)
  aura.addColorStop(0, "rgba(23,189,255,.25)")
  aura.addColorStop(.52, "rgba(42,83,242,.15)")
  aura.addColorStop(1, "rgba(20,47,140,0)")
  ctx.fillStyle = aura
  ctx.beginPath()
  ctx.arc(0, 0, 280, 0, Math.PI * 2)
  ctx.fill()

  ctx.save()
  ctx.globalCompositeOperation = "lighter"
  // Disco posterior: trajetórias não idênticas, brilho e sensação de perspectiva.
  for (let ring = 0; ring < 20; ring++) {
    const radius = 114 + ring * 4.4
    const wobble = Math.sin(progress * 18 + ring * .62) * 2.5
    ctx.beginPath()
    ctx.ellipse(0, 0, radius + wobble, 39 + ring * 1.6, -.35, Math.PI * .9, Math.PI * 1.95)
    ctx.strokeStyle = ring % 3 === 0 ? "rgba(180,94,255,.22)" : "rgba(35,191,255,.17)"
    ctx.lineWidth = ring % 4 === 0 ? 3.1 : 1.4
    ctx.shadowBlur = ring % 4 === 0 ? 12 : 3
    ctx.shadowColor = ring % 3 === 0 ? "#a34dff" : "#18c8ff"
    ctx.stroke()
  }
  ctx.restore()

  // Horizonte: centro realmente escuro; a borda tem a luz dobrada pela gravidade.
  const shadow = ctx.createRadialGradient(-15, -12, 20, 0, 0, 101)
  shadow.addColorStop(0, "#000006")
  shadow.addColorStop(.7, "#00030c")
  shadow.addColorStop(.91, "#02091d")
  shadow.addColorStop(1, "#34c9fa")
  ctx.fillStyle = shadow
  ctx.beginPath()
  ctx.arc(0, 0, 103, 0, Math.PI * 2)
  ctx.fill()

  // Arco frontal de acreção, partículas e distorções de luz.
  ctx.save()
  ctx.globalCompositeOperation = "lighter"
  for (let band = 0; band < 12; band++) {
    ctx.beginPath()
    ctx.ellipse(0, 0, 127 + band * 5.4, 43 + band * 2.2, -.35, .04, Math.PI * 1.03)
    ctx.strokeStyle = band % 3 === 0 ? "rgba(251,144,226,.45)" : "rgba(57,199,255,.38)"
    ctx.lineWidth = band % 4 === 0 ? 4.4 : 1.6
    ctx.shadowBlur = 10
    ctx.shadowColor = band % 3 === 0 ? "#d456ee" : "#14caff"
    ctx.stroke()
  }
  ctx.shadowBlur = 0
  for (let i = 0; i < 55; i++) {
    const a = random(i + 180) * Math.PI * 2 + progress * (2.4 + random(i + 719) * 2.8)
    const rad = 135 + 80 * random(i + 550)
    const x = Math.cos(a) * rad
    const y = Math.sin(a) * rad * .32 - Math.cos(a) * 32
    ctx.fillStyle = i % 3 ? "rgba(49,207,255,.56)" : "rgba(222,132,255,.6)"
    ctx.beginPath()
    ctx.arc(x, y, .8 + random(i + 95) * 2, 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.restore()
  ctx.restore()
}

function ProceduralUniverse({ progress }: { progress: number }) {
  const ref = useRef<HTMLCanvasElement>(null)
  const latestProgress = useRef(progress)
  latestProgress.current = progress
  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    drawSpace(canvas, progress)
  }, [progress])
  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const observer = new ResizeObserver(() => drawSpace(canvas, latestProgress.current))
    observer.observe(canvas)
    return () => observer.disconnect()
  }, [])
  return <canvas ref={ref} className="ao3-universe" aria-hidden="true" />
}

function Sheet({ index, progress }: { index: number; progress: number }) {
  const item = sheets[index]
  const born = index === 0 ? 1 : ease(.065 + index * .022, .16 + index * .025, progress)
  const scramble = ease(.24, .37, progress)
  const capture = ease(.43 + index * .006, .57 + index * .006, progress)
  const exit = ease(.6 + index * .005, .745 + index * .003, progress)
  const angle = index * Math.PI * .79 + (progress - .43) * (8.2 + index * .08)
  const radius = 196 + (index % 3) * 44
  const firstProductUnpacks = index === 0 ? ease(.05, .23, progress) : 1
  const beforeX = scatter[index][0] * lerp(.74, 1.08, scramble) * firstProductUnpacks
  const beforeY = scatter[index][1] * lerp(.7, 1.17, scramble) * firstProductUnpacks
  const orbitX = Math.cos(angle) * radius
  const orbitY = Math.sin(angle) * (74 + (index % 2) * 16)
  const x = lerp(beforeX, orbitX, capture)
  const y = lerp(beforeY, orbitY, capture)
  const depth = 1 + Math.sin(angle) * .19
  const rotation = lerp((index % 2 ? 1 : -1) * (9 + index * 4), Math.sin(angle) * 19, capture)
  // Flip controlado: duas faces programáticas, sem backface oculta do browser.
  const convert = ease(.49 + index * .008, .585 + index * .008, progress)
  const flip = Math.max(.07, Math.abs(Math.cos(convert * Math.PI)))
  const style: CSSProperties = {
    opacity: born * (1 - exit),
    transform: "translate3d(" + x.toFixed(1) + "px," + y.toFixed(1) + "px," + (capture * Math.sin(angle) * 80).toFixed(1) + "px) rotate(" + rotation.toFixed(2) + "deg) scaleX(" + flip.toFixed(3) + ") scale(" + (lerp(.87, depth, capture)).toFixed(3) + ")",
    zIndex: Math.sin(angle) > 0 ? 6 : 2,
  }
  return (
    <div className="ao3-sheet" style={style} aria-hidden="true">
      <div className="ao3-sheet-front" style={{ opacity: 1 - ease(.535 + index * .008, .545 + index * .008, progress) }}>
        <div className="ao3-sheet-top"><i /> PRODUTO {item.category}</div>
        <div className="ao3-product-graphic"><span className={"ao3-product-shape ao3-shape-" + (index % 3)} /></div>
        <strong>OPORTUNIDADE</strong>
        <span className="ao3-line" /><span className="ao3-line ao3-line-short" />
        <div className="ao3-card-foot">Adicionar ao fluxo <span>↗</span></div>
      </div>
      <div className="ao3-sheet-back" style={{ opacity: ease(.535 + index * .008, .545 + index * .008, progress) }}>
        <div className="ao3-sheet-top"><i /> {item.platform}</div>
        <div className="ao3-post-graphic"><span className="ao3-post-orb" /><span className="ao3-post-ring" /></div>
        <strong>DIVULGAÇÃO</strong>
        <small>Post preparado</small>
        <div className="ao3-card-foot">Rede selecionada <span>✓</span></div>
      </div>
      <span className="ao3-action">{item.action}</span>
    </div>
  )
}

const lines = [
  { start: 0, end: .24, first: "UMA OPORTUNIDADE.", second: "E TODO O TRABALHO DE DIVULGAR." },
  { start: .24, end: .37, first: "ABA. TEXTO. REDE.", second: "REPETIR. REPETIR. REPETIR." },
  { start: .37, end: .43, first: "PARE.", second: "E SE EXISTISSE OUTRA FORMA?" },
  { start: .43, end: .61, first: "ENTRE EM ÓRBITA.", second: "O CAOS ENCONTRA UM FLUXO." },
  { start: .61, end: .76, first: "MAIS CLAREZA.", second: "PRODUTOS · POSTS · DESTINOS." },
  { start: .76, end: 1.01, first: "", second: "" },
]

function KineticType({ progress }: { progress: number }) {
  const phrase = lines.find((line) => progress >= line.start && progress < line.end) || lines[lines.length - 1]
  const local = clamp((progress - phrase.start) / (phrase.end - phrase.start))
  const animate = (value: string, offset: number) => [...value].map((letter, i) => {
    const start = i / Math.max(1, value.length - 1) * .3 + offset
    const show = ease(start, start + .16, local)
    const leave = ease(.8, 1, local)
    return <span key={i} className="ao3-letter" style={{ opacity: show * (1 - leave), transform: "translateY(" + (62 * (1 - show) - leave * 35).toFixed(1) + "px) rotateX(" + (-75 * (1 - show)).toFixed(1) + "deg)" }}>{letter === " " ? "\u00a0" : letter}</span>
  })
  return <div className={"ao3-type" + (phrase.first === "PARE." ? " ao3-type-pause" : "")} aria-hidden="true">
    <div className="ao3-type-main">{animate(phrase.first, 0)}</div>
    <div className="ao3-type-sub">{animate(phrase.second, .13)}</div>
  </div>
}

function DashboardReveal({ progress }: { progress: number }) {
  const appear = ease(.602, .678, progress) * (1 - ease(.715, .785, progress))
  const style: CSSProperties = { opacity: appear, transform: "translate(-50%,-50%) perspective(850px) rotateX(" + ((1 - appear) * 23).toFixed(1) + "deg) scale(" + lerp(.72, 1, appear).toFixed(2) + ")" }
  return <div className="ao3-ui" style={style} aria-hidden="true">
    <aside className="ao3-ui-rail"><div className="ao3-ui-mark">◉</div><span>▦</span><span>☰</span><span>◷</span><span>⌁</span></aside>
    <section className="ao3-ui-body">
      <div className="ao3-ui-top"><div className="ao3-ui-brand">AUTO <b>ORBITAL</b></div><span className="ao3-ui-status">PAINEL</span></div>
      <div className="ao3-ui-title">Sua divulgação em um só lugar</div>
      <div className="ao3-ui-work">
        <div className="ao3-ui-product"><span className="ao3-product-illustration" /><div><small>PRODUTO</small><strong>Oportunidade organizada</strong><em>Selecionado para publicação</em></div></div>
        <div className="ao3-ui-separator">→</div>
        <div className="ao3-ui-destinations"><small>DESTINOS</small><div><b>Threads</b><b>Facebook</b><b>Instagram</b></div><span>Escolha as redes conectadas</span></div>
      </div>
      <div className="ao3-ui-schedule"><i /> POST PREPARADO <span>AGENDAR ▸</span></div>
    </section>
  </div>
}

function OrbitalSignature({ progress }: { progress: number }) {
  const show = ease(.755, .855, progress)
  return <div className="ao3-signature" style={{ opacity: show, transform: "translate(-50%,-50%) scale(" + lerp(.83, 1, show).toFixed(3) + ")" }} aria-hidden="true">
    <div className="ao3-signature-ring"><i className="ao3-signature-orbit"/><i className="ao3-signature-point"/></div>
    <div className="ao3-signature-word"><span>Auto</span><span className="ao3-signature-o">O</span><span>rbital</span></div>
    <p>Produtos encontram seu caminho. Sua rotina encontra mais controle.</p>
    <span className="ao3-future">AUTOMAÇÃO COMPLETA COM IA · EM DESENVOLVIMENTO</span>
  </div>
}

export default function OrbitalPilotPage() {
  const [time, setTime] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [reduced, setReduced] = useState(false)
  const startedAt = useRef<number | null>(null)
  const timeRef = useRef(0)
  useEffect(() => {
    const old = document.title
    document.title = "Auto Orbital — estudo de motion procedural V3"
    const media = window.matchMedia("(prefers-reduced-motion: reduce)")
    const listener = () => { setReduced(media.matches); if (media.matches) setPlaying(false) }
    listener()
    media.addEventListener("change", listener)
    return () => { document.title = old; media.removeEventListener("change", listener) }
  }, [])
  useEffect(() => {
    if (!playing || reduced) { startedAt.current = null; return }
    let frame = 0
    const tick = (stamp: number) => {
      if (startedAt.current === null) startedAt.current = stamp - timeRef.current
      const next = Math.min(DURATION_MS, stamp - startedAt.current)
      timeRef.current = next
      setTime(next)
      if (next >= DURATION_MS) { setPlaying(false); startedAt.current = null; return }
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => { cancelAnimationFrame(frame); startedAt.current = null }
  }, [playing, reduced])
  const progress = reduced ? 1 : time / DURATION_MS
  const chapterIndex = chapters.findIndex((chapter) => progress < chapter.until)
  const chapter = chapters[Math.max(0, chapterIndex)]
  const setTimeline = (value: number) => { const next = clamp(value, 0, DURATION_MS); setTime(next); timeRef.current = next; startedAt.current = null; setPlaying(false) }
  const togglePlay = () => {
    if (reduced) return
    if (playing) { setPlaying(false); return }
    if (timeRef.current >= DURATION_MS) { setTime(0); timeRef.current = 0 }
    setPlaying(true)
  }
  const active = 1 - ease(.73, .86, progress)
  return <div className="ao3-page">
    <header className="ao3-header"><a href="/presentation"><ArrowLeft size={17}/> Voltar à apresentação</a><span>EXPERIMENTO DE MOTION / V3</span><b>Auto Orbital</b></header>
    <main className="ao3-main">
      <div className="ao3-intro"><span>STORYBOARD / 10 SEGUNDOS / SEM SOM</span><h1>Do trabalho repetitivo à <em>órbita.</em></h1><p>Uma cena procedural: nenhum elemento visual é uma imagem colada. Cada movimento demonstra uma etapa do trabalho do afiliado.</p></div>
      <section className="ao3-frame" aria-label="Demonstração animada: uma ficha de produto se multiplica em tarefas, se organiza no horizonte de eventos e revela o fluxo de trabalho do Auto Orbital.">
        <div className="ao3-stage">
          <div className="ao3-grid" />
          <ProceduralUniverse progress={progress} />
          <div className="ao3-lens" style={{ opacity: ease(.39, .47, progress) * (1 - ease(.61, .73, progress)) }} />
          <div className="ao3-camera" style={{ opacity: active, transform: "perspective(950px) rotateX(" + lerp(8, -11, ease(.24, .42, progress)).toFixed(1) + "deg) rotateY(" + (Math.sin(progress * 13) * ease(.24, .62, progress) * 18).toFixed(1) + "deg) translate3d(" + (Math.sin(progress * 19) * ease(.2, .39, progress) * 24).toFixed(1) + "px,0,0)" }}>
            {sheets.map((_, i) => <Sheet key={i} index={i} progress={progress}/>)}
          </div>
          <KineticType progress={progress}/>
          <DashboardReveal progress={progress}/>
          <OrbitalSignature progress={progress}/>
          <div className="ao3-overlay-info"><span>AO / MOTION SYSTEM</span><span>{(progress * 10).toFixed(1)} / 10 S</span></div>
          <div className="ao3-vignette"/>
        </div>
        <div className="ao3-chapter"><span>ATO {String(chapterIndex + 1).padStart(2, "0")} / 06</span><strong>{chapter.title}</strong><small>{chapter.detail}</small><span>Silencioso · Renderização procedural</span></div>
      </section>
      <div className="ao3-controls">
        <button type="button" onClick={togglePlay} disabled={reduced}>{playing ? <Pause size={17}/> : <Play size={17}/>} {playing ? "Pausar" : time >= DURATION_MS ? "Reproduzir novamente" : "Reproduzir cena"}</button>
        <button type="button" className="ao3-replay" onClick={() => setTimeline(0)}><RotateCcw size={16}/> Reiniciar</button>
        <label htmlFor="ao3-timeline">EXPLORAR QUADROS / {Math.round(progress * 100)}%</label>
        <input id="ao3-timeline" type="range" min={0} max={DURATION_MS} step={50} value={reduced ? DURATION_MS : time} onChange={(e) => setTimeline(Number(e.target.value))} aria-label="Explorar quadros da cena"/>
      </div>
      <p className="ao3-disclaimer">Estudo criativo, ainda não aprovado. A coleta e publicação totalmente automáticas com IA continuam em desenvolvimento. Interface e anúncios são representações programáticas ilustrativas. O símbolo final é uma reconstrução procedural, não um novo arquivo de identidade oficial. Nenhuma imagem, som ou vídeo externo é usado nesta cena. A landing principal e o login permanecem inalterados.</p>
    </main>
  </div>
}
