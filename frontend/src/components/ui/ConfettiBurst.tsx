import { useEffect, useMemo, useState } from "react"
import "./confettiBurst.css"

const COLORS = [
  "var(--brand-electric-cyan)",
  "var(--brand-orbit-blue)",
  "var(--brand-ice-blue)",
  "var(--brand-indigo)",
  "var(--brand-orbital-violet)",
  "var(--brand-soft-lilac)",
]
const COUNT = 28
const DURATION_MS = 1200

function prefersReducedMotion(): boolean {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches
  } catch {
    return false
  }
}

/**
 * Explosão de confete a partir do centro do elemento pai (position: relative).
 * Cada `burstKey` novo dispara uma explosão. Sem dependências, usa só os tokens
 * de cor da marca e é omitida com prefers-reduced-motion.
 */
export function ConfettiBurst({ burstKey }: { burstKey: number }) {
  const [activeKey, setActiveKey] = useState(0)

  useEffect(() => {
    if (burstKey <= 0 || prefersReducedMotion()) return
    setActiveKey(burstKey)
    const timer = window.setTimeout(() => setActiveKey(0), DURATION_MS + 100)
    return () => window.clearTimeout(timer)
  }, [burstKey])

  const pieces = useMemo(() => Array.from({ length: COUNT }, (_, i) => {
    const angle = (i / COUNT) * Math.PI * 2 + (Math.random() - 0.5) * 0.5
    const distance = 70 + Math.random() * 90
    return {
      id: i,
      dx: Math.cos(angle) * distance,
      dy: Math.sin(angle) * distance - 30,
      rot: Math.round(Math.random() * 720 - 360),
      delay: Math.round(Math.random() * 90),
      color: COLORS[i % COLORS.length],
      round: i % 3 === 0,
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [activeKey])

  if (activeKey === 0) return null
  return (
    <span className="confetti-burst" aria-hidden="true">
      {pieces.map((p) => (
        <i key={p.id} className={p.round ? "is-round" : undefined}
          style={{
            "--dx": `${p.dx}px`, "--dy": `${p.dy}px`, "--rot": `${p.rot}deg`,
            "--delay": `${p.delay}ms`, background: p.color,
          } as React.CSSProperties} />
      ))}
    </span>
  )
}
