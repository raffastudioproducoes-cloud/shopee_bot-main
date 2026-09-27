import { useState } from "react"
import type { ReactNode, CSSProperties, MouseEvent } from "react"
import { Icon } from "./Icon"

export interface MoreLinkProps {
  children?: ReactNode
  href?: string
  /** true drops the chevron and underlines instead — the "Edit dashboard" form. */
  underline?: boolean
  onClick?: (e: MouseEvent<HTMLAnchorElement>) => void
  style?: CSSProperties
}

/** "See all ›" / "Edit dashboard" — the system's two link shapes. */
export function MoreLink({ children = "See all", href = "#", underline = false, onClick, style }: MoreLinkProps) {
  const [hot, setHot] = useState(false)
  return (
    <a
      href={href}
      onClick={onClick}
      onMouseEnter={() => setHot(true)}
      onMouseLeave={() => setHot(false)}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 2,
        font: "var(--fw-regular) var(--fs-caption)/1 var(--font-sans)",
        color: "inherit",
        opacity: hot ? 1 : 0.72,
        textDecoration: underline ? "underline" : "none",
        textUnderlineOffset: 3,
        whiteSpace: "nowrap",
        flex: "0 0 auto",
        transition: "opacity var(--dur-fast) var(--ease-standard)",
        ...style,
      }}
    >
      {children}
      {underline ? null : <Icon name="chevron-right" size={13} />}
    </a>
  )
}

export interface EyebrowProps {
  children?: ReactNode
  tone?: "muted" | "mint" | "inherit"
  style?: CSSProperties
}

/** Small uppercase tracked caption — "TOTAL BALANCE", "FROM USER PAIN POINTS…". */
export function Eyebrow({ children, tone = "muted", style }: EyebrowProps) {
  return (
    <span
      style={{
        display: "block",
        font: "var(--text-role-label)",
        letterSpacing: "var(--ls-label)",
        textTransform: "uppercase",
        color: tone === "muted" ? "var(--text-muted)" : tone === "mint" ? "var(--mint-400)" : "inherit",
        ...style,
      }}
    >
      {children}
    </span>
  )
}
