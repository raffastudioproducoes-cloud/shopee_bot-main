import type { CSSProperties } from "react"
import { Icon } from "./Icon"

export interface SegmentedOption {
  value: string
  label: string
  /** Lucide icon name shown before the label. */
  icon?: string
}

export interface SegmentedToggleProps {
  options: Array<SegmentedOption | string>
  value?: string
  onChange?: (value: string) => void
  tone?: "inset" | "glass"
  /** Outer height in px. 36 desktop, 44 mobile. */
  size?: number
  fullWidth?: boolean
  className?: string
  style?: CSSProperties
}

/** Two-or-three-up pill switch: From/To, Coin/NFT/Stake. Ported from the source
 *  design system's forms/SegmentedToggle.jsx (TSX + inline styles, same as the
 *  rest of this kit). */
export function SegmentedToggle({
  options,
  value,
  onChange,
  tone = "inset",
  size = 36,
  fullWidth = true,
  className = "",
  style,
}: SegmentedToggleProps) {
  const items = options.map((o) => (typeof o === "string" ? { value: o, label: o } : o))
  const active = value ?? items[0]?.value
  return (
    <div
      role="tablist"
      className={className}
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${items.length},1fr)`,
        gap: 4,
        padding: 4,
        borderRadius: "var(--r-pill)",
        width: fullWidth ? "100%" : "fit-content",
        background: tone === "inset" ? "var(--surface-inset)" : "rgba(255,255,255,.14)",
        ...style,
      }}
    >
      {items.map((it) => {
        const on = it.value === active
        return (
          <button
            key={it.value}
            type="button"
            role="tab"
            aria-selected={on}
            onClick={() => onChange?.(it.value)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 7,
              height: size - 8,
              border: "none",
              borderRadius: "var(--r-pill)",
              cursor: "pointer",
              background: on ? "rgba(255,255,255,.92)" : "transparent",
              color: on ? "var(--text-inverse)" : "var(--text-muted)",
              font: `${on ? "var(--fw-medium)" : "var(--fw-regular)"} var(--fs-body)/1 var(--font-sans)`,
              transition: "var(--t-hover)",
              whiteSpace: "nowrap",
            }}
          >
            {it.icon ? <Icon name={it.icon} size={14} /> : null}
            {it.label}
          </button>
        )
      })}
    </div>
  )
}
