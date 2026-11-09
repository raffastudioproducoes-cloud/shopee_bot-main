import { useEffect, useState } from 'react'
import { prefersReducedMotion } from '../../lib/motion'
import './postLoginSplash.css'

const SEEN_KEY = 'ao-post-login-splash'
export const SPLASH_MS = 1200

/** Decide se a entrada animada aparece: 1 vez por sessão, nunca com movimento reduzido. */
export function shouldShowPostLoginSplash(): boolean {
  if (prefersReducedMotion()) return false
  try { return sessionStorage.getItem(SEEN_KEY) !== '1' } catch { return false }
}

function markSeen() {
  try { sessionStorage.setItem(SEEN_KEY, '1') } catch { /* sem sessionStorage: aparece de novo, sem prejuízo */ }
}

/**
 * Tela rápida com a logo logo após o login: o painel já carrega por baixo e o círculo
 * se abre revelando-o. Não bloqueia cliques (pointer-events: none) e some sozinha em ~1,2 s.
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
      <img src="/brand/symbol-128.png" alt="" width={96} height={96} />
    </div>
  )
}
