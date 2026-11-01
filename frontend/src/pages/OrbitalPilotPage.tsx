import { useEffect, useRef, useState, type CSSProperties } from "react"
import { ArrowLeft, ArrowRight, CalendarDays, Check, Clock3, Layers3, Pause, Play, RotateCcw, Send, Sparkles } from "lucide-react"
import "./OrbitalPilotPage.css"

const DURATION_MS = 10_000

function ease(start: number, end: number, progress: number) {
  const t = Math.max(0, Math.min(1, (progress - start) / (end - start)))
  return t * t * (3 - 2 * t)
}

function timestamp(milliseconds: number) {
  const seconds = milliseconds / 1000
  return seconds.toFixed(1).replace(".", ",") + " s"
}

export default function OrbitalPilotPage() {
  const [time, setTime] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [reducedMotion, setReducedMotion] = useState(false)
  const timeRef = useRef(0)

  useEffect(() => {
    const previousTitle = document.title
    document.title = "Auto Orbital — piloto visual da transformação"
    const meta = document.createElement("meta")
    meta.name = "robots"
    meta.content = "noindex, nofollow"
    meta.dataset.orbitalPilot = "true"
    document.head.appendChild(meta)
    return () => { document.title = previousTitle; meta.remove() }
  }, [])

  useEffect(() => {
    if (!window.matchMedia) return
    const query = window.matchMedia("(prefers-reduced-motion: reduce)")
    const update = () => { setReducedMotion(query.matches); if (query.matches) setPlaying(false) }
    update()
    query.addEventListener("change", update)
    return () => query.removeEventListener("change", update)
  }, [])

  useEffect(() => {
    if (!playing || reducedMotion) return
    let frame = 0
    const start = performance.now() - timeRef.current
    const animate = (now: number) => {
      const next = Math.min(DURATION_MS, now - start)
      timeRef.current = next
      setTime(next)
      if (next >= DURATION_MS) { setPlaying(false); return }
      frame = requestAnimationFrame(animate)
    }
    frame = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frame)
  }, [playing, reducedMotion])

  const seek = (newTime: number) => {
    const next = Math.max(0, Math.min(DURATION_MS, newTime))
    setPlaying(false)
    timeRef.current = next
    setTime(next)
  }

  const toggle = () => {
    if (reducedMotion) return
    if (playing) { setPlaying(false); return }
    if (time >= DURATION_MS) {
      timeRef.current = 0
      setTime(0)
    }
    setPlaying(true)
  }

  const p = reducedMotion ? 1 : time / DURATION_MS
  const chaos = 1 - ease(0.34, 0.55, p)
  const gathering = ease(0.28, 0.5, p) * (1 - ease(0.73, 0.9, p))
  const system = ease(0.51, 0.68, p) * (1 - ease(0.83, 0.97, p))
  const brand = ease(0.76, 0.93, p)
  const light = ease(0.32, 0.51, p) * (1 - ease(0.82, 0.99, p) * 0.55)
  const current = p < 0.12 ? 0 : p < 0.37 ? 1 : p < 0.43 ? 2 : p < 0.62 ? 3 : p < 0.78 ? 4 : 5

  const beats = [
    { number: "01", title: "Uma oportunidade", text: "Um produto pode exigir várias etapas de divulgação." },
    { number: "02", title: "O acúmulo", text: "Copiar, adaptar e organizar horários ocupa espaço na rotina." },
    { number: "03", title: "Um instante de pausa", text: "A complexidade recua para dar lugar a um fluxo mais claro." },
    { number: "04", title: "A transformação orbital", text: "Os elementos dispersos se alinham ao redor de um processo." },
    { number: "05", title: "O produto em ação", text: "Produtos, conteúdos, agendamentos e acompanhamento em um só fluxo." },
    { number: "06", title: "Auto Orbital", text: "Você já encontra oportunidades. Organize também a forma de divulgá-las." },
  ]

  const previewStyle = {
    "--pilot-progress": String(p),
    "--pilot-light": String(light),
  } as CSSProperties

  return (
    <div className={"ao-pilot" + (reducedMotion ? " ao-pilot--reduced" : "")}>
      <header className="ao-pilot-header">
        <a className="ao-pilot-back" href="/presentation"><ArrowLeft size={17} /> Voltar à apresentação</a>
        <img className="ao-pilot-header-logo" src="/brand/wordmark.png" alt="Auto Orbital" />
        <span className="ao-pilot-version">Estudo visual · v1</span>
      </header>

      <main className="ao-pilot-main">
        <div className="ao-pilot-intro">
          <span className="ao-pilot-eyebrow"><span /> LABORATÓRIO ORBITAL / CENA 02</span>
          <h1>Do caos <em>à órbita.</em></h1>
          <p>Primeiro estudo de movimento da virada na landing. Sequência visual original, sem áudio e sem alterar o protótipo aprovado.</p>
        </div>

        <figure className="ao-pilot-figure">
          <div className="ao-pilot-stage" style={previewStyle} aria-label="Representação visual da passagem de tarefas dispersas para um fluxo organizado">
            <div className="ao-pilot-vignette" aria-hidden="true" />
            <div className="ao-pilot-particles" aria-hidden="true" />

            <div
              className="ao-pilot-chaos"
              style={{ opacity: chaos, transform: "scale(" + (1 + ease(0.2, 0.48, p) * 0.08) + ") translateY(" + (-ease(0.22, 0.49, p) * 26) + "px)" }}
              aria-hidden="true"
            >
              <div className="ao-pilot-product">
                <span className="ao-pilot-product-icon"><Layers3 size={31} strokeWidth={1.4} /></span>
                <small>UMA OPORTUNIDADE</small>
                <strong>Produto selecionado</strong>
                <span className="ao-pilot-product-line" />
                <span className="ao-pilot-product-line ao-pilot-product-line--short" />
              </div>
              <div className="ao-pilot-fragment ao-pilot-fragment--copy"><span><Layers3 size={15} /></span><b>Copiar</b><i /></div>
              <div className="ao-pilot-fragment ao-pilot-fragment--edit"><span><Sparkles size={15} /></span><b>Adaptar</b><i /></div>
              <div className="ao-pilot-fragment ao-pilot-fragment--schedule"><span><Clock3 size={15} /></span><b>Horários</b><i /></div>
              <div className="ao-pilot-fragment ao-pilot-fragment--send"><span><Send size={15} /></span><b>Publicar</b><i /></div>
              <div className="ao-pilot-chaos-orbit" />
            </div>

            <div
              className="ao-pilot-gather"
              style={{ opacity: gathering, transform: "translate(-50%, -50%) scale(" + (0.7 + ease(0.35, 0.58, p) * 0.46) + ") rotate(" + (p * 60 - 30) + "deg)" }}
              aria-hidden="true"
            >
              <div className="ao-pilot-ring ao-pilot-ring--a" />
              <div className="ao-pilot-ring ao-pilot-ring--b" />
              <div className="ao-pilot-gather-core" />
              <div className="ao-pilot-gather-star ao-pilot-gather-star--a" />
              <div className="ao-pilot-gather-star ao-pilot-gather-star--b" />
            </div>

            <div
              className="ao-pilot-system"
              style={{ opacity: system, transform: "translate(-50%, -50%) translateY(" + (32 - ease(0.51, 0.68, p) * 32) + "px) scale(" + (0.89 + ease(0.52, 0.71, p) * 0.11) + ")" }}
              aria-hidden="true"
            >
              <div className="ao-pilot-system-top">
                <div className="ao-pilot-system-identity"><img src="/brand/symbol.png" alt="" /><span>Fluxo de divulgação <small>Representação ilustrativa</small></span></div>
                <span className="ao-pilot-system-live"><i /> Organizado</span>
              </div>
              <div className="ao-pilot-system-track">
                <div><span><Layers3 size={19} /></span><strong>Produto</strong><small>Selecionar</small></div>
                <ArrowRight className="ao-pilot-system-arrow" size={18} />
                <div><span><Sparkles size={19} /></span><strong>Conteúdo</strong><small>Preparar</small></div>
                <ArrowRight className="ao-pilot-system-arrow" size={18} />
                <div><span><CalendarDays size={19} /></span><strong>Agenda</strong><small>Planejar</small></div>
                <ArrowRight className="ao-pilot-system-arrow" size={18} />
                <div><span><Check size={19} /></span><strong>Histórico</strong><small>Acompanhar</small></div>
              </div>
              <p>Ilustração do fluxo existente · disponibilidades dependem da rede e autorização.</p>
            </div>

            <div className="ao-pilot-brand-reveal" style={{ opacity: brand, transform: "translate(-50%, -50%) scale(" + (0.91 + ease(0.78, 0.97, p) * 0.09) + ")" }} aria-hidden="true">
              <div className="ao-pilot-brand-aura" />
              <img src="/brand/wordmark.png" alt="" />
              <p>Um fluxo mais organizado para suas divulgações.</p>
            </div>

            <div className="ao-pilot-frame-corner ao-pilot-frame-corner--tl" aria-hidden="true" />
            <div className="ao-pilot-frame-corner ao-pilot-frame-corner--br" aria-hidden="true" />
            <span className="ao-pilot-frame-label" aria-hidden="true">AUTO ORBITAL / VISUAL MOTION TEST</span>
            <span className="ao-pilot-frame-counter" aria-hidden="true">{timestamp(reducedMotion ? DURATION_MS : time)} / 10,0 s</span>
          </div>

          <figcaption className="ao-pilot-caption" aria-live="polite">
            <span className="ao-pilot-caption-index">{beats[current].number} / 06</span>
            <span><strong>{beats[current].title}</strong><small>{beats[current].text}</small></span>
            <span className="ao-pilot-caption-status">{reducedMotion ? "Imagem estática: movimento reduzido" : "Prévia ilustrativa · sem som"}</span>
          </figcaption>
        </figure>

        <div className="ao-pilot-controls" aria-label="Controles da prévia cinematográfica">
          <button type="button" className="ao-pilot-control-button ao-pilot-control-button--primary" onClick={toggle} disabled={reducedMotion}>
            {playing ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" />}
            {playing ? "Pausar" : time >= DURATION_MS ? "Reproduzir novamente" : "Reproduzir cena"}
          </button>
          <button type="button" className="ao-pilot-control-button" onClick={() => seek(0)} disabled={reducedMotion}>
            <RotateCcw size={17} /> Reiniciar
          </button>
          <label className="ao-pilot-scrub" htmlFor="ao-pilot-timeline">
            <span>Explorar os quadros</span>
            <input
              id="ao-pilot-timeline"
              type="range"
              min="0"
              max={DURATION_MS}
              step="50"
              value={reducedMotion ? DURATION_MS : time}
              disabled={reducedMotion}
              onChange={(event) => seek(Number(event.target.value))}
              aria-valuetext={timestamp(reducedMotion ? DURATION_MS : time)}
            />
          </label>
        </div>

        <div className="ao-pilot-notes">
          <p><strong>O que esta prévia valida:</strong> ritmo narrativo, transição da dispersão para a organização, contraste, composição e revelação com a arte oficial.</p>
          <p><strong>Ainda não é a versão final:</strong> não há vídeo renderizado, áudio, Scroll World sincronizado à rolagem ou interfaces reais capturadas. O protótipo da landing e o login permanecem inalterados.</p>
        </div>
      </main>
    </div>
  )
}
