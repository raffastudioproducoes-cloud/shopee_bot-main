import type { CSSProperties } from "react"
import { Icon } from "./Icon"

export interface DeltaChipProps {
  /** Pre-formatted string including sign and unit, e.g. "+ 3.14%" or "- 3.27%". */
  value: string
  /** Override the arrow direction; inferred from a leading "-" when omitted. */
  direction?: "up" | "down"
  size?: "sm" | "md"
  className?: string
  style?: CSSProperties
}

/** Signed percentage pill. Mint for up, salmon for down. */
export function DeltaChip({ value, direction, size = "md", className = "", style }: DeltaChipProps) {
  const dir = direction || (String(value).trim().startsWith("-") ? "down" : "up")
  const up = dir === "up"
  const sm = size === "sm"
  return (
    <span
      className={className}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 3,
        padding: sm ? "2px 7px" : "3px 9px",
        borderRadius: "var(--r-pill)",
        background: up ? "var(--mint-400)" : "var(--red-300)",
        color: up ? "var(--positive-ink)" : "var(--negative-ink)",
        font: `var(--fw-medium) ${sm ? "var(--fs-tiny)" : "var(--fs-small)"}/1 var(--font-numeric)`,
        fontVariantNumeric: "tabular-nums",
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      <Icon name={up ? "arrow-up-right" : "arrow-down-right"} size={sm ? 10 : 12} strokeWidth={2.25} />
      {value}
    </span>
  )
}

export interface DeltaTextProps {
  value: string
  direction?: "up" | "down"
  tone?: "dark" | "glass"
  className?: string
  style?: CSSProperties
}

/** The same signed value with no pill — used inside dense asset rows.
 *  `tone="glass"` switches to the ink-dark pair that stays legible on a glass panel. */
export function DeltaText({ value, direction, tone = "dark", className = "", style }: DeltaTextProps) {
  const dir = direction || (String(value).trim().startsWith("-") ? "down" : "up")
  const up = dir === "up"
  const glass = tone === "glass"
  return (
    <span
      className={className}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 3,
        color: glass
          ? up
            ? "var(--positive-on-glass)"
            : "var(--negative-on-glass)"
          : up
            ? "var(--green-600)"
            : "var(--red-400)",
        font: `var(--fw-medium) var(--fs-caption)/1 var(--font-numeric)`,
        fontVariantNumeric: "tabular-nums",
        whiteSpace: "nowrap",
        flex: "0 0 auto",
        ...style,
      }}
    >
      <Icon name={up ? "arrow-up-right" : "arrow-down-right"} size={11} strokeWidth={2.25} />
      {value}
    </span>
  )
}
