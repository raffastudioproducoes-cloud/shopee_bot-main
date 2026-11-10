import { useEffect, useRef, useState } from "react"
import { startOrbitScene } from "./orbitScene"
import "./loginOrbitScene.css"

/**
 * Animação da tela de login/cadastro ("Do caos à órbita", three.js): posts bagunçados se organizam
 * e fecham com a logo. Decorativa (aria-hidden). Sem WebGL, mostra o quadro final parado.
 */
export default function LoginOrbitScene() {
  const stage = useRef<HTMLDivElement>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const word = useRef<HTMLDivElement>(null)
  const flash = useRef<HTMLDivElement>(null)
  const end = useRef<HTMLDivElement>(null)
  const mark = useRef<HTMLImageElement>(null)
  const name = useRef<HTMLImageElement>(null)
  const tag = useRef<HTMLDivElement>(null)
  const sub = useRef<HTMLDivElement>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    const els = { stage: stage.current, canvas: canvas.current, word: word.current, flash: flash.current, end: end.current, mark: mark.current, name: name.current, tag: tag.current, sub: sub.current }
    if (Object.values(els).some((el) => !el)) return
    try {
      return startOrbitScene(els as Parameters<typeof startOrbitScene>[0])
    } catch {
      setFailed(true) // sem WebGL (aparelho antigo ou bloqueado): fica o quadro final parado
    }
  }, [])

  return (
    <div ref={stage} className={`login-orbit${failed ? " is-static" : ""}`} aria-hidden="true">
      <canvas ref={canvas} className="login-orbit__canvas" />
      <div className="login-orbit__layer login-orbit__vignette" />
      <div className="login-orbit__layer"><div ref={word} className="login-orbit__word" /></div>
      <div ref={flash} className="login-orbit__layer login-orbit__flash" />
      <div ref={end} className="login-orbit__layer login-orbit__end">
        <img ref={mark} className="login-orbit__mark" src="/brand/logo-mark.svg" alt="" />
        <img ref={name} className="login-orbit__name" src="/brand/logo-wordmark.svg" alt="" />
        <div ref={tag} className="login-orbit__tag">Do caos à órbita.</div>
        <div ref={sub} className="login-orbit__sub">Seus posts a um clique</div>
      </div>
    </div>
  )
}
