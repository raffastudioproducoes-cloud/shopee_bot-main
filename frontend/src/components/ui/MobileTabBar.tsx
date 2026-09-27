import type { CSSProperties } from "react"
import { Icon } from "./Icon"

/**
 * Floating mobile tab bar — five slots, the middle one a raised blue action.
 */
export interface MobileTabBarItem {
  value: string
  label: string
  /** Lucide icon name. */
  icon: string
  /** Raised blue centre action. */
  primary?: boolean
}

export interface MobileTabBarProps {
  items: MobileTabBarItem[]
  value?: string
  onSelect?: (value: string) => void
  className?: string
  style?: CSSProperties
}

/** Floating mobile tab bar. The centre item is a raised blue circle. */
export function MobileTabBar({ items, value, onSelect, className = "", style }: MobileTabBarProps) {
  const active = value ?? items[0]?.value
  return (
    <nav
      className={className}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        height: "var(--tabbar-h)",
        padding: "0 18px",
        borderRadius: "var(--r-pill)",
        background: "rgba(20,32,45,.82)",
        backdropFilter: "var(--blur-chrome)",
        border: "1px solid var(--border-hairline)",
        boxShadow: "var(--shadow-float)",
        ...style,
      }}
    >
      {items.map((it) => {
        const on = it.value === active
        if (it.primary) {
          return (
            <button
              key={it.value}
              type="button"
              aria-label={it.label}
              onClick={() => onSelect?.(it.value)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: 48,
                height: 48,
                borderRadius: "50%",
                border: "none",
                background: "var(--sky-400)",
                color: "#0E1A26",
                cursor: "pointer",
                boxShadow: "var(--shadow-float)",
              }}
            >
              <Icon name={it.icon} size={22} strokeWidth={2} />
            </button>
          )
        }
        return (
          <button
            key={it.value}
            type="button"
            aria-label={it.label}
            onClick={() => onSelect?.(it.value)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 40,
              height: 40,
              borderRadius: "50%",
              border: "none",
              cursor: "pointer",
              background: on ? "var(--white)" : "transparent",
              color: on ? "var(--black)" : "var(--text-muted)",
              transition: "var(--t-hover)",
            }}
          >
            <Icon name={it.icon} size={19} strokeWidth={on ? 2 : 1.6} />
          </button>
        )
      })}
    </nav>
  )
}
