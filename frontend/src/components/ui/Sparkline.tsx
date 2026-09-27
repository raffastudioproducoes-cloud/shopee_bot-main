import { useId } from "react"
import type { CSSProperties } from "react"

export interface SparklineProps {
  /** Raw series; scaled to fit. 8–14 points reads best at card size. */
  data?: number[]
  width?: number
  /** 38 on stat cards, 62 on the "Best to buy" card. */
  height?: number
  color?: string
  strokeWidth?: number
  /** Adds the faint gradient wash under the line — mobile asset cards only. */
  fill?: boolean
  className?: string
  style?: CSSProperties
}

/** Flat white polyline — no fill, no axes, no dots. */
export function Sparkline({
  data,
  width = 120,
  height = 38,
  color = "var(--chart-line)",
  strokeWidth = 1.5,
  fill = false,
  className = "",
  style,
}: SparklineProps) {
  const pts = data && data.length ? data : [4, 9, 6, 12, 8, 14, 10, 16, 12, 18]
  const min = Math.min(...pts)
  const max = Math.max(...pts)
  const span = max - min || 1
  const step = pts.length > 1 ? width / (pts.length - 1) : width
  const pad = strokeWidth
  const coords = pts.map((v, i) => [i * step, pad + (1 - (v - min) / span) * (height - pad * 2)])
  const line = coords.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ")
  const area = `${line} ${width},${height} 0,${height}`
  const id = useId().replace(/:/g, "")
  return (
    <svg
      className={className}
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      style={{ display: "block", overflow: "visible", ...style }}
      aria-hidden="true"
    >
      {fill ? (
        <>
          <defs>
            <linearGradient id={`g${id}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.28" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </linearGradient>
          </defs>
          <polygon points={area} fill={`url(#g${id})`} />
        </>
      ) : null}
      <polyline
        points={line}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}
