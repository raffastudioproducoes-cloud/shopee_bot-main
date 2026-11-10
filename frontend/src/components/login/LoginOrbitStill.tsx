import "./loginOrbitScene.css"

/** Quadro final parado da animação do login: usado com "reduzir movimento" e enquanto a cena 3D carrega. */
export function LoginOrbitStill() {
  return (
    <div className="login-orbit is-static" aria-hidden="true">
      <div className="login-orbit__layer login-orbit__vignette" />
      <div className="login-orbit__layer login-orbit__end">
        <img className="login-orbit__mark" src="/brand/logo-mark-static.svg" alt="" />
        <img className="login-orbit__name" src="/brand/logo-wordmark.svg" alt="" />
        <div className="login-orbit__tag">Do caos à órbita.</div>
        <div className="login-orbit__sub">Seus posts a um clique</div>
      </div>
    </div>
  )
}
