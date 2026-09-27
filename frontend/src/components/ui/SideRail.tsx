import type { CSSProperties } from "react"
import { Icon } from "./Icon"
import { IconButton } from "./IconButton"

/**
 * Desktop side rail — brand mark, icon nav with tracked caps labels, support button.
 */
export interface SideRailItem {
  value: string
  label: string
  /** Lucide icon name. */
  icon: string
}

export interface SideRailProps {
  items: SideRailItem[]
  value?: string
  onSelect?: (value: string) => void
  /** Path to the brand mark image. */
  logoSrc?: string
  /** Fallback wordmark when no image is given. */
  brand?: string
  support?: boolean
  onSupport?: () => void
  className?: string
  style?: CSSProperties
}

/** 72px desktop rail: mark at the top, icon + tracked caps labels, support at the foot. */
export function SideRail({
  items,
  value,
  onSelect,
  logoSrc,
  brand = "MT",
  support = true,
  onSupport,
  className = "",
  style,
}: SideRailProps) {
  const active = value ?? items[0]?.value
  return (
    <nav
      className={className}
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 26,
        width: "var(--rail-w)",
        flex: "0 0 auto",
        padding: "18px 0 20px",
        background: "var(--bg-rail)",
        ...style,
      }}
    >
      <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", height: 30 }}>
        {logoSrc ? (
          <img src={logoSrc} alt={brand} style={{ height: 18, width: "auto", display: "block" }} />
        ) : (
          <span
            style={{
              font: "var(--fw-bold) 18px/1 var(--font-display)",
              letterSpacing: "var(--ls-tight)",
              color: "var(--white)",
            }}
          >
            {brand}
          </span>
        )}
      </span>
      <ul style={{ display: "flex", flexDirection: "column", gap: 22, margin: 0, padding: 0, listStyle: "none", width: "100%" }}>
        {items.map((it) => {
          const on = it.value === active
          return (
            <li key={it.value}>
              <button
                type="button"
                onClick={() => onSelect?.(it.value)}
                style={{
                  display: "grid",
                  justifyItems: "center",
                  gap: 5,
                  width: "100%",
                  padding: "6px 0",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: on ? "var(--white)" : "var(--text-faint)",
                  transition: "var(--t-hover)",
                }}
              >
                <Icon name={it.icon} size={20} strokeWidth={on ? 2 : 1.6} />
                <span
                  style={{
                    font: "var(--fw-medium) var(--fs-micro)/1 var(--font-sans)",
                    letterSpacing: "var(--ls-rail)",
                    textTransform: "uppercase",
                  }}
                >
                  {it.label}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
      {support ? (
        <IconButton icon="message-square" label="Support" tone="rail" size={34} onClick={onSupport} style={{ marginTop: "auto" }} />
      ) : null}
    </nav>
  )
}
