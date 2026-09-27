import { useState } from "react"
import type { CSSProperties, MouseEvent } from "react"
import { Icon } from "./Icon"

export interface IconButtonProps {
  /** Lucide icon name. */
  icon: string
  /** Accessible label — also the tooltip. */
  label: string
  /** dark = solid black (refresh on "Best to buy").
   *  accent = sky-blue fill (the expand FAB that straddles a panel corner).
   *  glass = translucent white (top-bar bell).
   *  rail = blue-tinted (support bubble at the foot of the side rail).
   *  plain = transparent. */
  tone?: "dark" | "accent" | "glass" | "rail" | "plain"
  /** Diameter in px. 30 inline, 36 top bar, 40 FAB. Use >= 44 on mobile. */
  size?: number
  /** Red unread dot, top-right. */
  badge?: boolean
  active?: boolean
  onClick?: (e: MouseEvent<HTMLButtonElement>) => void
  className?: string
  style?: CSSProperties
}

const TONES: Record<string, { bg: string; fg: string }> = {
  dark: { bg: "var(--black)", fg: "var(--white)" },
  accent: { bg: "var(--sky-400)", fg: "#0E1A26" },
  glass: { bg: "rgba(255,255,255,.14)", fg: "var(--text-body)" },
  rail: { bg: "rgba(129,189,250,.18)", fg: "var(--sky-300)" },
  plain: { bg: "transparent", fg: "var(--text-muted)" },
}

/** Circular icon-only control — bell, refresh, expand, support. */
export function IconButton({
  icon,
  label,
  tone = "glass",
  size = 36,
  badge = false,
  active = false,
  onClick,
  className = "",
  style,
}: IconButtonProps) {
  const t = TONES[tone] || TONES.glass
  const [hot, setHot] = useState(false)
  const [down, setDown] = useState(false)
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      onMouseEnter={() => setHot(true)}
      onMouseLeave={() => {
        setHot(false)
        setDown(false)
      }}
      onMouseDown={() => setDown(true)}
      onMouseUp={() => setDown(false)}
      className={className}
      style={{
        position: "relative",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: size,
        height: size,
        borderRadius: "var(--r-pill)",
        border: "none",
        background: active ? "rgba(255,255,255,.26)" : t.bg,
        color: t.fg,
        cursor: "pointer",
        filter: hot ? "brightness(1.12)" : "none",
        transform: down ? "scale(var(--press-scale))" : "none",
        transition: "var(--t-hover), var(--t-press), filter var(--dur-fast) var(--ease-standard)",
        ...style,
      }}
    >
      <Icon name={icon} size={Math.round(size * 0.46)} />
      {badge ? (
        <span
          style={{
            position: "absolute",
            top: 5,
            right: 6,
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: "var(--red-400)",
            boxShadow: "0 0 0 2px rgba(0,0,0,.35)",
          }}
        />
      ) : null}
    </button>
  )
}
