import type { CSSProperties, ReactNode } from "react"

type SkeletonProps = { width?: CSSProperties["width"]; height?: CSSProperties["height"]; radius?: CSSProperties["borderRadius"]; className?: string }

export function Skeleton({ width = "100%", height = 16, radius = "var(--r-sm)", className }: SkeletonProps) {
  return <span aria-hidden="true" className={`skeleton ${className ?? ""}`} style={{ width, height, borderRadius: radius }} />
}

export function SkeletonText({ lines = 2 }: { lines?: number }) {
  return <span className="skeleton-stack">{Array.from({ length: lines }, (_, i) => <Skeleton key={i} width={i === lines - 1 ? "72%" : "100%"} />)}</span>
}

export function SkeletonCard({ children }: { children?: ReactNode }) {
  return <div className="skeleton-card" aria-hidden="true">{children ?? <><Skeleton width="42%" height={12} /><Skeleton width="68%" height={28} /></>}</div>
}

export function SkeletonTableRow({ columns = 4 }: { columns?: number }) {
  return <div className="skeleton-table-row" aria-hidden="true">{Array.from({ length: columns }, (_, i) => <Skeleton key={i} width={i === 0 ? "28%" : "18%"} />)}</div>
}

export function SkeletonAvatar({ size = 48 }: { size?: number }) {
  return <Skeleton width={size} height={size} radius="var(--r-token)" />
}

export function SkeletonRegion({ children }: { children: ReactNode }) {
  return <div role="status" aria-busy="true" aria-live="polite" aria-label="Carregando conteúdo">{children}</div>
}
