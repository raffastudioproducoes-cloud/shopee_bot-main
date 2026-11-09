import { useEffect, useRef, useState } from 'react'
import { countUpValue } from './countUp'

/** Preferência do sistema por menos movimento (WCAG 2.3.3). Falha segura: sem matchMedia, assume movimento reduzido. */
export function prefersReducedMotion(): boolean {
  try {
    return typeof window.matchMedia !== 'function' || window.matchMedia('(prefers-reduced-motion: reduce)').matches
  } catch {
    return true
  }
}

const COUNTED_KEY = 'ao-counted'

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
 * Contagem de 0 até `target` só na primeira exibição de cada rótulo na sessão.
 * Com movimento reduzido, valor 0 ou repetição, devolve o valor final na hora (sem atrasar dado real).
 */
export function useCountUp(target: number, label: string, durationMs = 700): number {
  const skip = prefersReducedMotion() || !Number.isFinite(target) || target <= 0 || alreadyCounted(label)
  const [value, setValue] = useState(skip ? target : 0)
  const frame = useRef(0)

  useEffect(() => {
    if (skip) { setValue(target); return }
    const start = performance.now()
    const tick = (now: number) => {
      const progress = (now - start) / durationMs
      setValue(countUpValue(target, progress))
      if (progress < 1) frame.current = requestAnimationFrame(tick)
      else markCounted(label)
    }
    frame.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame.current)
  }, [target, label, durationMs, skip])

  return value
}
