import { useState } from "react"
import type { CSSProperties, MouseEvent } from "react"
import { TokenBadge } from "./TokenBadge"
import { DeltaChip } from "./DeltaChip"
import { Sparkline } from "./Sparkline"

/**
 * Dark coin card for the dashboard's top strip — badge, name, sparkline, price, delta.
 */
export interface StatCardProps {
  /** Coin name, e.g. "Bitcoin". Repurposed as the stat label, e.g. "Produtos Cadastrados". */
  name: string
  /** Ticker under the name, e.g. "BTC". */
  ticker?: string
  /** Glyph inside the coin badge, e.g. "₿". */
  symbol?: string
  /** Lucide icon name, used instead of `symbol`. */
  icon?: string
  /** Formatted price string, e.g. "$8,560". Repurposed as the stat value. */
  price: string
  /** Signed percentage, e.g. "+ 3.14%" / "- 3.27%". */
  delta?: string
  /** Sparkline series. Omit to skip rendering the sparkline entirely. */
  data?: number[]
  /** Render the sparkline row. Default true to match the source card; set false for plain counts. */
  showSparkline?: boolean
  onClick?: (e: MouseEvent<HTMLDivElement>) => void
  className?: string
  style?: CSSProperties
}

/** Dark coin card from the dashboard's top strip: badge, name/ticker,
 *  sparkline, price, delta chip. Four sit in a row. */
export function StatCard({
  name,
  ticker,
  symbol,
  icon,
  price,
  delta,
  data,
  showSparkline = true,
  onClick,
  className = "",
  style,
}: StatCardProps) {
  const [hot, setHot] = useState(false)
  return (
    <div
      className={className}
      onClick={onClick}
      onMouseEnter={() => setHot(true)}
      onMouseLeave={() => setHot(false)}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 10,
        padding: "var(--pad-card)",
        borderRadius: "var(--r-md)",
        background: hot ? "var(--surface-card-hover)" : "var(--surface-card)",
        border: "1px solid var(--border-card)",
        boxShadow: "var(--shadow-card)",
        cursor: onClick ? "pointer" : "default",
        transition: "var(--t-hover)",
        ...style,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
        <TokenBadge symbol={symbol} icon={icon} size={28} />
        <span style={{ display: "grid" }}>
          <span style={{ font: "var(--fw-medium) var(--fs-small)/1.25 var(--font-sans)", color: "var(--text-display)" }}>{name}</span>
          {ticker ? (
            <span style={{ font: "var(--fw-regular) var(--fs-tiny)/1.35 var(--font-sans)", color: "var(--text-faint)" }}>{ticker}</span>
          ) : null}
        </span>
      </div>
      {showSparkline ? <Sparkline data={data} width={140} height={42} style={{ width: "100%" }} /> : null}
      <span
        style={{
          font: "var(--fw-medium) var(--fs-price)/1 var(--font-numeric)",
          letterSpacing: "var(--ls-tight)",
          color: "var(--text-display)",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {price}
      </span>
      {delta ? <DeltaChip value={delta} size="sm" style={{ alignSelf: "flex-start" }} /> : null}
    </div>
  )
}
