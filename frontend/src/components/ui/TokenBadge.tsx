import type { ReactNode, CSSProperties } from "react"
import { Icon } from "./Icon"

export interface TokenBadgeProps {
  /** One or two characters — "₿", "Ð", "$", "T". Ignored when `icon` is set. */
  symbol?: ReactNode
  /** Lucide icon name, used instead of a glyph. */
  icon?: string
  /** Diameter. 26 in dense rows, 30 on stat cards, 34 in asset lists. */
  size?: number
  tone?: "black" | "mint" | "glass"
  className?: string
  style?: CSSProperties
}

/** Circular black coin badge. Holds a currency glyph, a ticker letter or an icon. */
export function TokenBadge({ symbol, icon, size = 30, tone = "black", className = "", style }: TokenBadgeProps) {
  const bg = tone === "black" ? "var(--black)" : tone === "mint" ? "var(--green-600)" : "rgba(255,255,255,.16)"
  return (
    <span
      className={className}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: size,
        height: size,
        flex: "0 0 auto",
        borderRadius: "var(--r-token)",
        background: bg,
        color: "var(--white)",
        font: `var(--fw-semibold) ${Math.round(size * 0.44)}px/1 var(--font-sans)`,
        boxShadow: "inset 0 0 0 1px rgba(255,255,255,.08)",
        ...style,
      }}
    >
      {icon ? <Icon name={icon} size={Math.round(size * 0.54)} /> : symbol}
    </span>
  )
}
