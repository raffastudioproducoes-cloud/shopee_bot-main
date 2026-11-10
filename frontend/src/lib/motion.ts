import { useEffect, useRef, useState } from 'react'
import { countUpEase } from './countUp'

/** Preferência do sistema por menos movimento (WCAG 2.3.3). Falha segura: sem matchMedia, assume movimento reduzido. */
export function prefersReducedMotion(): boolean {
  try {
    return typeof window.matchMedia !== 'function' || window.matchMedia('(prefers-reduced-motion: reduce)').matches
  } catch {
    return true
  }
}

const COUNTED_KEY = 'ao-counted'
const SPLASH_KEY = 'ao-post-login-splash'

/** Chamada a cada login: a entrada com a logo e as contagens voltam a aparecer (não só na primeira vez da aba). */
export function resetPostLoginAnimations(): void {
  try { sessionStorage.removeItem(SPLASH_KEY); sessionStorage.removeItem(COUNTED_KEY) } catch { /* sem sessionStorage */ }
}

function alreadyCounted(label: string): boolean {
  try { return (sessionStorage.getItem(COUNTED_KEY) ?? '').split('|').includes(label) } catch { return false }
}

function markCounted(label: string) {
  try {
    const seen = (sessionStorage.getItem(COUNTED_KEY) ?? '').split('|').filter(Boolean)
    if (!seen.includes(label)) sessionStorage.setItem(COUNTED_KEY, [...seen, label].join('|'))
  } catch { /* sessionStorage indisponível: apenas conta de novo */ }
}

/**
 * Fração 0→1 da animação de contagem, no ritmo "devagar no início, acelera no fim". Os números, as barras e
 * os anéis usam a mesma fração para encher juntos. Só roda na primeira exibição de cada rótulo na sessão;
 * com movimento reduzido ou repetição, devolve 1 na hora (sem atrasar dado real).
 */
export function useCountProgress(label: string, durationMs = 1100): number {
  const skip = prefersReducedMotion() || alreadyCounted(label)
  const [fraction, setFraction] = useState(skip ? 1 : 0)
  const frame = useRef(0)

  useEffect(() => {
    if (skip) { setFraction(1); return }
    const start = performance.now()
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / durationMs)
      setFraction(countUpEase(progress))
      if (progress < 1) frame.current = requestAnimationFrame(tick)
      else markCounted(label)
    }
    frame.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame.current)
  }, [label, durationMs, skip])

  return fraction
}

/** Contagem de 0 até `target` acompanhando `useCountProgress`. Alvo inválido ou zero aparece como está. */
export function useCountUp(target: number, label: string, durationMs = 1100): number {
  const fraction = useCountProgress(label, durationMs)
  if (!Number.isFinite(target) || target <= 0) return Math.max(0, Math.trunc(target || 0))
  return Math.min(target, Math.round(target * fraction))
}
