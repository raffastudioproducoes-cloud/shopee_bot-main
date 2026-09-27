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

export interface TileProps {
  icon: string
  /** 40 on category rows, 34 in summary rows. */
  size?: number
  radius?: string
  tone?: "black" | "glass" | "mint"
  className?: string
  style?: CSSProperties
}

/** Rounded-square black tile — the category icon on Cash / Investment / Crypto. */
export function Tile({ icon, size = 40, radius = "var(--r-md)", tone = "black", className = "", style }: TileProps) {
  const bg = tone === "black" ? "var(--black)" : tone === "glass" ? "rgba(255,255,255,.14)" : "var(--green-600)"
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
        borderRadius: radius,
        background: bg,
        color: "var(--white)",
        ...style,
      }}
    >
      <Icon name={icon} size={Math.round(size * 0.5)} />
    </span>
  )
}

export interface GlyphRingProps {
  icon: string
  /** 40 on timeline pages, 48 on challenge cards. */
  size?: number
  className?: string
  style?: CSSProperties
}

/** Hairline circle holding a mint glyph — the case-study page motif. */
export function GlyphRing({ icon, size = 48, className = "", style }: GlyphRingProps) {
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
        borderRadius: "50%",
        border: "1px solid rgba(255,255,255,.3)",
        color: "var(--mint-400)",
        ...style,
      }}
    >
      <Icon name={icon} size={Math.round(size * 0.42)} />
    </span>
  )
}
