import type { CSSProperties } from "react"

type OrbitalLoaderProps = {
  size?: "sm" | "md" | "lg"
  label?: string
  fullScreen?: boolean
}

const sizes = { sm: 128, md: 190, lg: 260 } as const

function OrbitIcon({ type }: { type: string }) {
  const paths: Record<string, string> = {
    video: "M6 5h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Zm10 5 4-2v8l-4-2M8 9l4 3-4 3Z",
    post: "M6 3h9l4 4v14H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm9 0v5h4M8 12h8M8 16h6",
    image: "M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6Zm3 10 3-3 2 2 2-2 3 3M15 9h.01",
    thread: "M12 20a8 8 0 1 1 8-8 7 7 0 0 1-2 5M8 12a4 4 0 1 1 4 4v-4",
    heart: "m12 20-1.5-1.4C5 13.6 2 10.8 2 7.5A4.5 4.5 0 0 1 6.5 3c1.7 0 3.3.8 4.5 2.1A6 6 0 0 1 15.5 3 4.5 4.5 0 0 1 20 7.5c0 3.3-3 6.1-8.5 11.1L12 20Z",
    calendar: "M5 4h14a2 2 0 0 1 2 2v13H3V6a2 2 0 0 1 2-2Zm-2 5h18M8 2v4M16 2v4M8 13h.01M12 13h.01M16 13h.01",
  }
  const d = paths[type]
  if (!d) return null
  return <svg viewBox="0 0 24 24" aria-hidden="true" className="orbital-loader__icon"><path d={d} /></svg>
}

export function OrbitalLoader({ size = "md", label = "Carregando dados…", fullScreen = false }: OrbitalLoaderProps) {
  const style = { "--orbital-size": `${sizes[size]}px` } as CSSProperties
  return (
    <div className={`orbital-loader orbital-loader--${size}${fullScreen ? " orbital-loader--fullscreen" : ""}`} role="status" aria-live="polite" style={style}>
      <div className="orbital-loader__scene" aria-hidden="true">
        <div className="orbital-loader__orbit orbital-loader__orbit--back"><OrbitIcon type="video" /><OrbitIcon type="thread" /><OrbitIcon type="calendar" /></div>
        <img className="orbital-loader__blackhole" src="/brand/logo-mark.svg" alt="" />
        <div className="orbital-loader__orbit orbital-loader__orbit--front"><OrbitIcon type="post" /><OrbitIcon type="image" /><OrbitIcon type="heart" /></div>
      </div>
      <span className="orbital-loader__label">{label}</span>
    </div>
  )
}
