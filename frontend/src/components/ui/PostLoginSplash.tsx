import { useEffect, useState } from 'react'
import { prefersReducedMotion } from '../../lib/motion'
import './motion.css'

const SEEN_KEY = 'ao-post-login-splash'
export const SPLASH_MS = 2200

/** Aparece a cada login (e ao reabrir o site com sessão ativa), para qualquer conta, inclusive ADM. */
export function shouldShowPostLoginSplash(): boolean {
  if (prefersReducedMotion()) return false
  try { return sessionStorage.getItem(SEEN_KEY) !== '1' } catch { return false }
}

function markSeen() {
  try { sessionStorage.setItem(SEEN_KEY, '1') } catch { /* sem sessionStorage: aparece de novo, sem prejuízo */ }
}

/**
 * Entrada depois do login: a logo aparece com brilho e um anel que expande, sobe para o canto do menu
 * enquanto um círculo se abre revelando o dashboard (que entra em cascata, com números contando).
 * Não bloqueia cliques (pointer-events: none); toque ou tecla encerra na hora; some sozinha em ~2,2 s.
 */
export function PostLoginSplash() {
  const [visible, setVisible] = useState(shouldShowPostLoginSplash)

  useEffect(() => {
    if (!visible) return
    markSeen()
    const timer = window.setTimeout(() => setVisible(false), SPLASH_MS)
    const skip = () => setVisible(false)
    window.addEventListener('keydown', skip, { once: true })
    window.addEventListener('pointerdown', skip, { once: true })
    return () => {
      window.clearTimeout(timer)
      window.removeEventListener('keydown', skip)
      window.removeEventListener('pointerdown', skip)
    }
  }, [visible])

  if (!visible) return null
  return (
    <div className="post-login-splash" aria-hidden="true">
      <span className="post-login-splash__ring" />
      <span className="post-login-splash__ring post-login-splash__ring--late" />
      <img className="post-login-splash__logo" src="/brand/logo-mark.svg" alt="" width={220} height={220} />
      <img className="post-login-splash__name" src="/brand/logo-wordmark.svg" alt="" width={230} height={47} />
    </div>
  )
}
