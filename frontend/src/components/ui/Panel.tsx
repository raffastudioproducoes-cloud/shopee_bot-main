import type { ReactNode, CSSProperties, MouseEvent } from "react"

/**
 * Container surface.
 */
export interface PanelProps {
  children?: ReactNode
  /** glass = the signature lit steel-to-navy panel (Top Assets, Fiat Balance, the Crypto category card).
   *  glass-quiet = the same gradient at low opacity, for secondary blocks.
   *  dark = flat navy card with a hairline (stat cards, Transactions, Summary).
   *  coal = near-black card for case-study / marketing pages.
   *  bare = layout-only, no paint. */
  surface?: "glass" | "glass-quiet" | "dark" | "coal" | "bare"
  radius?: string
  padding?: number | string
  /** Turn off when a FAB has to straddle the panel edge. */
  overflowHidden?: boolean
  className?: string
  style?: CSSProperties
  onClick?: (e: MouseEvent<HTMLElement>) => void
}

const SURFACES: Record<string, CSSProperties> = {
  glass: {
    background: "var(--panel-glass)",
    boxShadow: "var(--shadow-panel), var(--inner-lit-strong)",
    border: "1px solid rgba(255,255,255,.18)",
    color: "var(--text-on-glass)",
  },
  "glass-quiet": {
    background: "var(--panel-glass-quiet)",
    boxShadow: "var(--shadow-panel), var(--inner-lit)",
    border: "1px solid rgba(255,255,255,.12)",
    color: "var(--text-body)",
  },
  dark: {
    background: "var(--surface-card)",
    boxShadow: "var(--shadow-card)",
    border: "1px solid var(--border-card)",
    color: "var(--text-body)",
  },
  coal: {
    background: "var(--surface-marketing-card)",
    boxShadow: "none",
    border: "1px solid transparent",
    color: "var(--text-body)",
  },
  bare: { background: "transparent", boxShadow: "none", border: "1px solid transparent" },
}

/** The system's container. Every block on a screen is one of these. */
export function Panel({
  children,
  surface = "dark",
  radius = "var(--r-lg)",
  padding = 0,
  overflowHidden = true,
  className = "",
  style,
  onClick,
}: PanelProps) {
  const s = SURFACES[surface] || SURFACES.dark
  return (
    <section
      className={className}
      onClick={onClick}
      style={{
        position: "relative",
        borderRadius: radius,
        padding,
        overflow: overflowHidden ? "hidden" : "visible",
        backdropFilter: surface.startsWith("glass") ? "var(--blur-glass)" : undefined,
        ...s,
        ...style,
      }}
    >
      {children}
    </section>
  )
}

export interface PanelHeaderProps {
  title: ReactNode
  /** Show the circled "i" affordance that sits beside most panel titles. */
  info?: boolean
  /** Right-hand slot — usually a MoreLink or an IconButton. */
  trailing?: ReactNode
  onInfo?: () => void
  className?: string
  style?: CSSProperties
}

/** Header strip inside a Panel: title, optional info dot, optional trailing node. */
export function PanelHeader({ title, info = false, trailing, onInfo, className = "", style }: PanelHeaderProps) {
  return (
    <header
      className={className}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 10,
        padding: "14px 16px 12px",
        ...style,
      }}
    >
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          minWidth: 0,
          font: "var(--text-role-title)",
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
        }}
      >
        {title}
        {info ? (
          <button
            type="button"
            aria-label={`About ${title}`}
            onClick={onInfo}
            style={{
              display: "inline-flex",
              width: 15,
              height: 15,
              borderRadius: "50%",
              border: "1px solid currentColor",
              alignItems: "center",
              justifyContent: "center",
              background: "none",
              cursor: "pointer",
              opacity: 0.55,
              font: "var(--fw-semibold) 9px/1 var(--font-sans)",
              padding: 0,
            }}
          >
            i
          </button>
        ) : null}
      </span>
      {trailing ? <span style={{ display: "inline-flex", alignItems: "center", flex: "0 0 auto" }}>{trailing}</span> : null}
    </header>
  )
}

export interface DividerProps {
  tone?: "dark" | "glass"
  style?: CSSProperties
}

/** Hairline row divider matching the asset tables. */
export function Divider({ tone = "dark", style }: DividerProps) {
  return (
    <div
      role="separator"
      style={{
        height: 1,
        background: tone === "glass" ? "var(--border-on-glass)" : "var(--border-hairline)",
        ...style,
      }}
    />
  )
}
