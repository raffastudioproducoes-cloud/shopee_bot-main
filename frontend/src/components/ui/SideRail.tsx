import { useLayoutEffect, useRef, useState } from "react"
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
  /** Mobile drawer state (styled via `.app-rail[data-open]` in index.css). */
  open?: boolean
  id?: string
  className?: string
  style?: CSSProperties
}

/** Desktop rail (--rail-w): mark at the top, icon + tracked caps labels, support at the foot. */
export function SideRail({
  items,
  value,
  onSelect,
  logoSrc,
  brand = "MT",
  support = true,
  onSupport,
  open,
  id,
  className = "",
  style,
}: SideRailProps) {
  const active = value ?? items[0]?.value
  // Pílula que desliza até o item da página atual (E1). Mede o <li> ativo; se não achar, fica escondida.
  const listRef = useRef<HTMLUListElement>(null)
  const [pill, setPill] = useState<{ y: number; h: number } | null>(null)
  useLayoutEffect(() => {
    const measure = () => {
      const li = listRef.current?.querySelector<HTMLElement>('li[data-active="true"]')
      setPill(li && li.offsetHeight > 0 ? { y: li.offsetTop, h: li.offsetHeight } : null)
    }
    measure()
    window.addEventListener("resize", measure)
    return () => window.removeEventListener("resize", measure)
  }, [active, items.length, open])
  return (
    <nav
      id={id}
      aria-label="Navegação principal"
      data-open={open ? "true" : "false"}
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
      <span className="csp-s-0133">
        {logoSrc ? (
          <img src={logoSrc} alt={brand} className="csp-s-0134" />
        ) : (
          <span
            className="csp-s-0135"
          >
            {brand}
          </span>
        )}
      </span>
      <div style={{ position: "relative", width: "100%" }}>
      {pill ? <span aria-hidden="true" className="app-rail-pill" style={{ transform: `translateY(${pill.y}px)`, height: pill.h }} /> : null}
      <ul className="csp-s-0136" ref={listRef} style={{ position: "relative" }}>
        {items.map((it) => {
          const on = it.value === active
          return (
            <li key={it.value} data-active={on ? "true" : undefined}>
              <button
                type="button"
                className="app-rail-item"
                aria-current={on ? "page" : undefined}
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
                  className="app-rail-label"
                  style={{
                    maxWidth: "calc(var(--rail-w) - 8px)",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
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
      </div>
      {support ? (
        <IconButton icon="message-square" label="Support" tone="rail" size={34} onClick={onSupport} style={{ marginTop: "auto" }} />
      ) : null}
    </nav>
  )
}
