import { useEffect, useRef, useState, type CSSProperties } from "react"
import { ArrowLeft, Check, Pause, Play, RotateCcw } from "lucide-react"
import "./OrbitalPilotPage.css"

// V2: estudo cinematográfico original, sem áudio. Imagem da marca NÃO é desenhada no código.
const DURATION_MS = 9_600
const PAPER_COUNT = 9
const clamp = (value: number, a = 0, b = 1) => Math.max(a, Math.min(b, value))
const smooth = (a: number, b: number, value: number) => {
  const t = clamp((value - a) / (b - a))
  return t * t * (3 - 2 * t)
}
const mix = (a: number, b: number, t: number) => a + (b - a) * t

function shot(progress: number) {
  const frames = [
    { at: 0, rx: 16, ry: -21, rz: -9, scale: 1.18, x: -70, y: 24 },
    { at: .16, rx: -5, ry: 19, rz: 7, scale: 1.35, x: 70, y: 18 },
    { at: .32, rx: 14, ry: -27, rz: -13, scale: 1.52, x: -65, y: -18 },
    { at: .43, rx: -22, ry: 36, rz: 19, scale: 1.72, x: 43, y: 7 },
    { at: .55, rx: 26, ry: -36, rz: -24, scale: 1.3, x: -18, y: 4 },
    { at: .72, rx: -13, ry: 23, rz: 12, scale: 1.18, x: 22, y: 4 },
    { at: .86, rx: 0, ry: -4, rz: -2, scale: 1.06, x: 0, y: 0 },
    { at: 1, rx: 0, ry: 0, rz: 0, scale: 1, x: 0, y: 0 },
  ]
  let index = frames.findIndex((frame) => frame.at > progress)
  if (index === -1) index = frames.length - 1
  const end = frames[index]
  const begin = frames[Math.max(0, index - 1)]
  const t = smooth(begin.at, end.at, progress)
  return {
    rx: mix(begin.rx, end.rx, t),
    ry: mix(begin.ry, end.ry, t),
    rz: mix(begin.rz, end.rz, t),
    scale: mix(begin.scale, end.scale, t),
    x: mix(begin.x, end.x, t),
    y: mix(begin.y, end.y, t),
  }
}

const headlines = [
  { from: 0, to: .16, top: "UM PRODUTO.", bottom: "UM PONTO DE PARTIDA." },
  { from: .16, to: .3, top: "COPIAR.", bottom: "ADAPTAR. REPETIR." },
  { from: .3, to: .43, top: "E MAIS UMA VEZ.", bottom: "EM CADA REDE." },
  { from: .43, to: .57, top: "PARE.", bottom: "IMAGINE OUTRO FLUXO." },
  { from: .57, to: .74, top: "TUDO EM ÓRBITA.", bottom: "PRODUTOS VIRAM DIVULGAÇÃO." },
  { from: .74, to: .87, top: "UM CICLO.", bottom: "UMA OPERAÇÃO MAIS CLARA." },
  { from: .87, to: 1.01, top: "", bottom: "" },
]

const chapters = [
  { at: .16, title: "O ponto de partida", detail: "Uma oportunidade exige preparação." },
  { at: .3, title: "A repetição", detail: "Produtos, textos e redes competem por atenção." },
  { at: .43, title: "A sobrecarga", detail: "Cada publicação manual acrescenta outra tarefa." },
  { at: .57, title: "O horizonte de eventos", detail: "Os produtos começam a entrar em um único fluxo." },
  { at: .74, title: "A transformação", detail: "Papéis se tornam peças de divulgação em uma órbita." },
  { at: .87, title: "O ciclo orbital", detail: "A visão de uma operação cada vez mais automática." },
  { at: 1.01, title: "Auto Orbital", detail: "Sua operação de afiliados em uma nova órbita." },
]

function Paper({ index, progress }: { index: number; progress: number }) {
  const entry = index === 0 ? 1 : smooth(.02 + index * .013, .2 + index * .014, progress)
  const crowd = smooth(.18, .36, progress)
  const gravity = smooth(.39, .57, progress)
  const orbit = smooth(.51, .63, progress)
  const exit = smooth(.84, .95, progress)
  const initialAngle = index * 2.3999
  const spread = index === 0 ? 0 : 105 + index * 22
  const originalX = Math.cos(initialAngle) * spread
  const originalY = Math.sin(initialAngle) * spread * .7
  const scatteredX = originalX + (index % 2 ? 55 : -68) * crowd
  const scatteredY = originalY + (index % 3 - 1) * 38 * crowd
  const spin = initialAngle + (progress - .4) * 15.5
  const spiralRadius = mix(210, 130, gravity)
  const spiralX = Math.cos(spin) * spiralRadius
  const spiralY = Math.sin(spin) * spiralRadius * .47
  const orbitalAngle = initialAngle + (progress - .57) * 16
  const orbitalX = Math.cos(orbitalAngle) * 228
  const orbitalY = Math.sin(orbitalAngle) * 92
  const x = mix(scatteredX, mix(spiralX, orbitalX, orbit), gravity)
  const y = mix(scatteredY, mix(spiralY, orbitalY, orbit), gravity)
  const z = gravity * (36 + Math.sin(orbitalAngle) * 145)
  const conversion = smooth(.51, .68, progress)
  const switchToAd = smooth(.57, .62, progress)
  const turn = mix(-13 + index * 9 + crowd * 25, 0, conversion)
  const flip = Math.max(.08, Math.abs(Math.cos(conversion * Math.PI)))
  const rot = mix((index - 4) * 14, Math.sin(orbitalAngle) * 23, gravity)
  const scale = mix(.72 + (index % 3) * .09, .78 + (Math.sin(orbitalAngle) + 1) * .16, gravity)
  const opacity = entry * (1 - exit)
  const style: CSSProperties = {
    opacity,
    transform: "translate3d(" + x.toFixed(1) + "px," + y.toFixed(1) + "px," + z.toFixed(1) + "px) rotateZ(" + rot.toFixed(1) + "deg) rotateY(" + turn.toFixed(1) + "deg) scaleX(" + flip.toFixed(2) + ") scale(" + scale.toFixed(2) + ")",
    zIndex: gravity > .5 && Math.sin(orbitalAngle) < 0 ? 1 : 5,
  }
  return (
    <div className="ao-film-paper" style={style} aria-hidden="true">
      <div className="ao-film-paper-face ao-film-paper-face--product" style={{ opacity: 1 - switchToAd }}>
        <span className="ao-film-page-index">CATÁLOGO / {String(index + 1).padStart(2, "0")}</span>
        <div className="ao-film-product-thumb"><span /><i /><b /></div>
        <strong>PRODUTO</strong>
        <i className="ao-film-paper-line" /><i className="ao-film-paper-line short" />
        <span className="ao-film-paper-price">OPORTUNIDADE</span>
      </div>
      <div className="ao-film-paper-face ao-film-paper-face--ad" style={{ opacity: switchToAd }}>
        <div className="ao-film-ad-signal"><span /> PEÇA PRONTA</div>
        <div className="ao-film-ad-visual"><span /></div>
        <strong>DIVULGAÇÃO</strong>
        <small>Conteúdo preparado</small>
        <div className="ao-film-ad-footer"><span /><span /><span /></div>
      </div>
    </div>
  )
}

function KineticText({ progress }: { progress: number }) {
  const phrase = headlines.find((entry) => progress >= entry.from && progress < entry.to) || headlines[headlines.length - 1]
  const local = clamp((progress - phrase.from) / Math.max(.01, phrase.to - phrase.from))
  const reveal = (line: string, second: boolean) =>
    line.split("").map((letter, index) => {
      const at = (index / Math.max(1, line.length - 1)) * .34 + (second ? .2 : 0)
      const enter = smooth(at, at + .18, local)
      const leave = smooth(.82, 1, local)
      return <span key={index} className="ao-film-glyph" style={{ opacity: enter * (1 - leave), transform: "translate3d(0," + ((1 - enter) * 75 - leave * 30).toFixed(1) + "px,0) rotateX(" + ((1 - enter) * -70).toFixed(1) + "deg)" }}>{letter === " " ? "\u00a0" : letter}</span>
    })
  return (
    <div key={phrase.from} className={"ao-film-typography" + (progress >= .4 && progress < .58 ? " ao-film-typography--focus" : "")} aria-hidden="true">
      <div className="ao-film-type-top">{reveal(phrase.top, false)}</div>
      <div className="ao-film-type-bottom">{reveal(phrase.bottom, true)}</div>
    </div>
  )
}

export default function OrbitalPilotPage() {
  const [time, setTime] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [reducedMotion, setReducedMotion] = useState(false)
  const currentTime = useRef(0)

  useEffect(() => {
    const oldTitle = document.title
    document.title = "Auto Orbital — horizonte de eventos · estudo v2"
    const meta = document.createElement("meta")
    meta.name = "robots"
    meta.content = "noindex, nofollow"
    meta.dataset.orbitalPilot = "true"
    document.head.appendChild(meta)
    return () => { document.title = oldTitle; meta.remove() }
  }, [])

  useEffect(() => {
    if (!window.matchMedia) return
    const media = window.matchMedia("(prefers-reduced-motion: reduce)")
    const handleChange = () => { setReducedMotion(media.matches); if (media.matches) setPlaying(false) }
    handleChange()
    media.addEventListener("change", handleChange)
    return () => media.removeEventListener("change", handleChange)
  }, [])

  useEffect(() => {
    if (!playing || reducedMotion) return
    const start = performance.now() - currentTime.current
    let frame = 0
    const tick = (now: number) => {
      const next = Math.min(DURATION_MS, now - start)
      currentTime.current = next
      setTime(next)
      if (next >= DURATION_MS) { setPlaying(false); return }
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [playing, reducedMotion])

  const seek = (value: number) => {
    const next = clamp(value, 0, DURATION_MS)
    setPlaying(false)
    currentTime.current = next
    setTime(next)
  }
  const toggle = () => {
    if (reducedMotion) return
    if (playing) { setPlaying(false); return }
    if (time >= DURATION_MS) {
      currentTime.current = 0
      setTime(0)
    }
    setPlaying(true)
  }
  const p = reducedMotion ? 1 : time / DURATION_MS
  const camera = shot(p)
  const cameraTransform = "translate3d(" + camera.x + "px," + camera.y + "px,0) rotateX(" + camera.rx + "deg) rotateY(" + camera.ry + "deg) rotateZ(" + camera.rz + "deg) scale(" + camera.scale + ")"
  const horizonAppear = smooth(.38, .51, p)
  const finale = smooth(.86, .98, p)
  const currentChapter = chapters.find((chapter) => p < chapter.at) || chapters[chapters.length - 1]
  const particles = Array.from({ length: 40 }, (_, index) => index)

  return (
    <div className={"ao-film" + (reducedMotion ? " ao-film--reduced" : "")}>
      <header className="ao-film-header">
        <a href="/presentation" className="ao-film-back"><ArrowLeft size={17} /> Voltar à apresentação</a>
        <span className="ao-film-topnote"><i /> PROTÓTIPO CINEMATOGRÁFICO / V2</span>
        <img src="/brand/wordmark.png" alt="Auto Orbital" />
      </header>

      <main className="ao-film-main">
        <section className="ao-film-intro">
          <div className="ao-film-kicker">A VIRADA / HORIZONTE DE EVENTOS</div>
          <h1>Produtos entram. <em>Divulgações ganham órbita.</em></h1>
          <p>Nova direção visual: movimento de câmera, tipografia cinética e transformação de produtos em peças de divulgação. Estudo conceitual, sem áudio.</p>
        </section>

        <figure className="ao-film-figure">
          <div className="ao-film-stage" aria-label="Estudo visual: produtos em papéis convergem para o horizonte de eventos do Auto Orbital e se transformam em anúncios organizados num ciclo de órbita">
            <div className="ao-film-space" aria-hidden="true" />
            <div className="ao-film-stars" aria-hidden="true">
              {particles.map((index) => {
                const x = (index * 137.23) % 100
                const y = (index * 73.83) % 100
                const depth = .5 + (index % 5) * .22
                return <span key={index} style={{ left: x + "%", top: y + "%", opacity: .25 + .55 * Math.abs(Math.sin(p * 18 + index)), transform: "translate3d(" + (Math.sin(p * 9 + index) * 30 * depth).toFixed(1) + "px," + (Math.cos(p * 6 + index) * 22 * depth).toFixed(1) + "px,0) scale(" + depth + ")" }} />
              })}
            </div>
            <div className="ao-film-camera" style={{ transform: cameraTransform }} aria-hidden="true">
              <div className="ao-film-horizon" style={{ opacity: horizonAppear * (1 - finale * .18), transform: "translate(-50%, -50%) scale(" + mix(.55, 1.08, smooth(.39, .63, p)) + ")" }}>
                <div className="ao-film-event-light" />
                <img src="/brand/symbol.png" alt="" className="ao-film-original-mark" />
                <div className="ao-film-arc ao-film-arc--front" />
                <div className="ao-film-arc ao-film-arc--back" />
              </div>
              <div className="ao-film-orbiters">
                {Array.from({ length: PAPER_COUNT }, (_, i) => <Paper key={i} index={i} progress={p} />)}
              </div>
            </div>
            <KineticText progress={p} />
            <div className="ao-film-flash" style={{ opacity: smooth(.355, .375, p) * (1 - smooth(.385, .405, p)) * .68 + smooth(.51, .53, p) * (1 - smooth(.54, .56, p)) * .4 }} aria-hidden="true" />
            <div className="ao-film-final" style={{ opacity: finale, transform: "translate(-50%, -50%) scale(" + mix(1.16, 1, finale) + ")" }} aria-hidden="true">
              <img src="/brand/symbol.png" className="ao-film-final-symbol" alt="" />
              <img src="/brand/wordmark.png" className="ao-film-final-name" alt="" />
              <p>O futuro da divulgação dos afiliados está tomando forma.</p>
              <span className="ao-film-final-status"><Check size={12} /> VISÃO DE AUTOMAÇÃO EM DESENVOLVIMENTO</span>
            </div>
            <span className="ao-film-filmcode" aria-hidden="true">AO / V2 · CINEMATIC PROOF</span>
            <span className="ao-film-timing" aria-hidden="true">{((reducedMotion ? DURATION_MS : time) / 1000).toFixed(1).replace(".", ",")} / 9,6 S</span>
            <div className="ao-film-safe-edge" aria-hidden="true" />
          </div>
          <figcaption className="ao-film-caption" aria-live="polite">
            <div><span className="ao-film-beat">CENA {String(chapters.indexOf(currentChapter) + 1).padStart(2, "0")} / 07</span><strong>{currentChapter.title}</strong><small>{currentChapter.detail}</small></div>
            <span>Sem áudio · Direção conceitual</span>
          </figcaption>
        </figure>

        <div className="ao-film-controls">
          <button type="button" className="ao-film-play" onClick={toggle} disabled={reducedMotion}>
            {playing ? <Pause size={17} fill="currentColor" /> : <Play size={17} fill="currentColor" />}
            {playing ? "Pausar" : time >= DURATION_MS ? "Reproduzir novamente" : "Reproduzir cena"}
          </button>
          <button type="button" className="ao-film-restart" onClick={() => seek(0)} disabled={reducedMotion}><RotateCcw size={17} /> Reiniciar</button>
          <label htmlFor="ao-pilot-timeline" className="ao-film-timeline">
            <span>EXPLORAR A SEQUÊNCIA / {(p * 100).toFixed(0)}%</span>
            <input id="ao-pilot-timeline" type="range" min="0" max={DURATION_MS} step="50" value={reducedMotion ? DURATION_MS : time} disabled={reducedMotion} onChange={(event) => seek(Number(event.target.value))} aria-valuetext={((reducedMotion ? DURATION_MS : time) / 1000).toFixed(1) + " segundos"} />
          </label>
        </div>
        <div className="ao-film-disclaimer">
          <p>A cena é uma visão artística: coleta e postagem totalmente automáticas com IA ainda estão em desenvolvimento. Os papéis e anúncios são ilustrativos, não registros de publicações reais.</p>
          <p>O horizonte de eventos e as peças de mídia vêm do símbolo oficial. O arquivo da marca é exibido intacto. O login, a landing aprovada e a produção não são alterados nesta prévia.</p>
        </div>
      </main>
    </div>
  )
}
