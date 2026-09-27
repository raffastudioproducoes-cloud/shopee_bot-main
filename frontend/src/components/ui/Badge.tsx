import type { ReactNode, CSSProperties } from "react"

export interface BadgeProps {
  children?: ReactNode
  /** mint = current / emphasised item. neutral = every other item in the run.
   *  outline = hairline only. glass = for use over a glass Panel. */
  tone?: "mint" | "neutral" | "outline" | "glass"
  /** lg is the case-study page size (17px, 11/22 padding). */
  size?: "md" | "lg"
  className?: string
  style?: CSSProperties
}

const TONES: Record<string, { bg: string; fg: string; bd?: string }> = {
  mint: { bg: "var(--mint-400)", fg: "var(--black)" },
  neutral: { bg: "var(--coal-700)", fg: "var(--text-body)" },
  outline: { bg: "transparent", fg: "var(--text-muted)", bd: "1px solid var(--border-hairline)" },
  glass: { bg: "rgba(255,255,255,.16)", fg: "var(--text-body)" },
}

/** Pill label. The case-study pages use mint for the active step and
 *  neutral grey for every other step in a sequence. */
export function Badge({ children, tone = "neutral", size = "md", className = "", style }: BadgeProps) {
  const t = TONES[tone] || TONES.neutral
  const lg = size === "lg"
  return (
    <span
      className={className}
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: lg ? "11px 22px" : "6px 14px",
        borderRadius: "var(--r-pill)",
        background: t.bg,
        color: t.fg,
        border: t.bd || "1px solid transparent",
        font: `var(--fw-regular) ${lg ? "var(--fs-subtitle)" : "var(--fs-body)"}/1.1 var(--font-sans)`,
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {children}
    </span>
  )
}
