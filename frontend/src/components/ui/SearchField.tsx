import { useState } from "react"
import type { ChangeEvent, CSSProperties } from "react"
import { Icon } from "./Icon"

export interface SearchFieldProps {
  value?: string
  onChange?: (e: ChangeEvent<HTMLInputElement>) => void
  /** Por padrão a palavra "Buscar". */
  placeholder?: string
  /** 220 on desktop top bar; "100%" on mobile. */
  width?: number | string
  /** Height in px. 36 desktop, 44 mobile. */
  size?: number
  tone?: "inset" | "glass"
  className?: string
  style?: CSSProperties
}

/** Top-bar search pill. */
export function SearchField({
  value,
  onChange,
  placeholder = "Buscar",
  width = 220,
  size = 36,
  tone = "inset",
  className = "",
  style,
}: SearchFieldProps) {
  const [hot, setHot] = useState(false)
  return (
    <label
      onMouseEnter={() => setHot(true)}
      onMouseLeave={() => setHot(false)}
      className={className}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 9,
        height: size,
        width,
        padding: "0 14px",
        borderRadius: "var(--r-pill)",
        background: tone === "inset" ? "var(--surface-inset)" : "rgba(255,255,255,.12)",
        border: `1px solid ${hot ? "var(--border-strong)" : "var(--border-hairline)"}`,
        transition: "var(--t-hover)",
        cursor: "text",
        ...style,
      }}
    >
      <Icon name="search" size={15} style={{ color: "var(--text-muted)" }} />
      <input
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        style={{
          flex: 1,
          minWidth: 0,
          background: "none",
          border: "none",
          outline: "none",
          color: "var(--text-body)",
          font: "var(--text-role-body)",
        }}
      />
    </label>
  )
}
