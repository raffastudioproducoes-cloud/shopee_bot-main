import { useState } from "react"
import type { ReactNode, CSSProperties, MouseEvent } from "react"
import { Icon } from "./Icon"

/**
 * The one text button in the MT system.
 */
export interface ButtonProps {
  children?: ReactNode
  /** primary = near-white fill on dark (Buy / Cash out / Smart trade).
   *  secondary = translucent white fill (Set Alert).
   *  dark = solid black (refresh, menu actions).
   *  mint = brand mint fill, black ink (marketing CTAs).
   *  buy / send = transparent with green / salmon hairline (balance rows).
   *  glass = white fill for use on top of a glass Panel.
   *  ghost = text only. */
  variant?: "primary" | "secondary" | "dark" | "mint" | "buy" | "send" | "glass" | "ghost"
  size?: "sm" | "md" | "lg"
  /** Lucide icon name rendered before the label. */
  icon?: string
  /** Lucide icon name rendered after the label. */
  iconAfter?: string
  fullWidth?: boolean
  disabled?: boolean
  /** Shows a spinner in place of the leading icon and blocks clicks. */
  loading?: boolean
  onClick?: (e: MouseEvent<HTMLButtonElement>) => void
  type?: "button" | "submit" | "reset"
  className?: string
  style?: CSSProperties
  title?: string
}

const SIZES = {
  sm: { h: 30, px: 12, fs: "var(--fs-small)", r: "var(--r-sm)", gap: 6 },
  md: { h: 38, px: 16, fs: "var(--fs-body)", r: "var(--r-md)", gap: 8 },
  lg: { h: 46, px: 22, fs: "var(--fs-body-lg)", r: "var(--r-md)", gap: 8 },
}

const TONES: Record<string, { bg: string; fg: string; bd: string; fw: string }> = {
  primary: { bg: "#E8F1FB", fg: "var(--black)", bd: "1px solid transparent", fw: "var(--fw-semibold)" },
  secondary: { bg: "rgba(255,255,255,.16)", fg: "var(--text-body)", bd: "1px solid transparent", fw: "var(--fw-medium)" },
  dark: { bg: "var(--black)", fg: "var(--white)", bd: "1px solid transparent", fw: "var(--fw-medium)" },
  mint: { bg: "var(--mint-400)", fg: "var(--black)", bd: "1px solid transparent", fw: "var(--fw-semibold)" },
  buy: { bg: "transparent", fg: "var(--text-body)", bd: "1px solid var(--border-buy)", fw: "var(--fw-medium)" },
  send: { bg: "transparent", fg: "var(--text-body)", bd: "1px solid var(--border-send)", fw: "var(--fw-medium)" },
  glass: { bg: "rgba(255,255,255,.88)", fg: "var(--text-inverse)", bd: "1px solid transparent", fw: "var(--fw-medium)" },
  ghost: { bg: "transparent", fg: "var(--text-muted)", bd: "1px solid transparent", fw: "var(--fw-medium)" },
}

/** The one text button in the system. */
export function Button({
  children,
  variant = "primary",
  size = "md",
  icon,
  iconAfter,
  fullWidth = false,
  disabled = false,
  loading = false,
  onClick,
  type = "button",
  className = "",
  style,
  title,
}: ButtonProps) {
  const s = SIZES[size] || SIZES.md
  const t = TONES[variant] || TONES.primary
  const [hot, setHot] = useState(false)
  const [down, setDown] = useState(false)
  const isInactive = disabled || loading
  const hasFill = t.bg !== "transparent"
  const leadingIcon = loading ? "loader-2" : icon
  return (
    <button
      type={type}
      title={title}
      disabled={isInactive}
      aria-disabled={disabled}
      aria-busy={loading}
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
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: s.gap,
        minHeight: Math.max(s.h, 44),
        padding: `0 ${s.px}px`,
        width: fullWidth ? "100%" : undefined,
        font: `${t.fw} ${s.fs}/1 var(--font-sans)`,
        letterSpacing: "var(--ls-tight)",
        background: t.bg,
        color: t.fg,
        border: t.bd,
        borderRadius: s.r,
        cursor: isInactive ? "not-allowed" : "pointer",
        opacity: isInactive ? 0.38 : 1,
        boxShadow: !hasFill ? "none" : down && !isInactive ? "var(--shadow-pressed)" : "var(--shadow-card)",
        filter: hot && !isInactive ? "brightness(1.08)" : "none",
        transform: down && !isInactive ? "scale(var(--press-scale))" : "none",
        transition:
          "var(--t-hover), var(--t-press), filter var(--dur-fast) var(--ease-standard), box-shadow var(--dur-fast) var(--ease-standard)",
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {leadingIcon ? (
        <Icon name={leadingIcon} size={size === "sm" ? 14 : 16} className={loading ? "animate-spin" : undefined} />
      ) : null}
      {children}
      {iconAfter ? <Icon name={iconAfter} size={size === "sm" ? 14 : 16} /> : null}
    </button>
  )
}
