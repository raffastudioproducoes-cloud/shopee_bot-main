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
  return <div role="status" aria-busy="true" aria-label="Carregando conteúdo">{children}</div>
}

export type PageSkeletonVariant = "cards" | "table" | "form" | "detail" | "list"

/** Quantidade padrão de blocos por variante; `count` em PageSkeleton sobrescreve. */
export const SKELETON_ROWS: Record<PageSkeletonVariant, number> = { cards: 4, table: 5, list: 4, form: 4, detail: 2 }

type PageSkeletonProps = {
  variant?: PageSkeletonVariant
  heading?: boolean
  titleWidth?: CSSProperties["width"]
  subtitleWidth?: CSSProperties["width"]
  /** Botão de ação à direita do título. */
  action?: boolean
  /** Barra de filtros (chips) abaixo do título. */
  toolbar?: boolean
  /** Quantidade de blocos; padrão em SKELETON_ROWS. */
  count?: number
  /** Colunas de cada linha da variante "table". */
  columns?: number
}

const range = (n: number) => Array.from({ length: n }, (_, i) => i)

export function PageSkeleton({ variant = "detail", heading = true, titleWidth = "220px", subtitleWidth = "300px", action = false, toolbar = false, count = SKELETON_ROWS[variant], columns = 4 }: PageSkeletonProps) {
  const items = range(count)
  return (
    <SkeletonRegion>
      <div className="page-skeleton" data-variant={variant}>
        {heading && (
          <div className="page-skeleton-header">
            <div className="page-skeleton-heading"><Skeleton width={titleWidth} height={34} /><Skeleton className="skeleton-sub" width={subtitleWidth} /></div>
            {action && <Skeleton width={112} height={38} />}
          </div>
        )}
        {toolbar && <div className="page-skeleton-toolbar"><Skeleton width={86} height={34} /><Skeleton width={86} height={34} /></div>}
        {variant === "cards" && <div className="page-skeleton-grid">{items.map((i) => <SkeletonCard key={i} />)}</div>}
        {variant === "table" && <div className="page-skeleton-table">{items.map((i) => <SkeletonTableRow key={i} columns={columns} />)}</div>}
        {variant === "list" && <div className="page-skeleton-list">{items.map((i) => <SkeletonCard key={i} />)}</div>}
        {variant === "form" && <div className="page-skeleton-form">{items.map((i) => <Skeleton key={i} height={42} />)}</div>}
        {variant === "detail" && <>{items.map((i) => <SkeletonCard key={i} />)}</>}
      </div>
    </SkeletonRegion>
  )
}

export function PageState({ loading, skeleton, children }: { loading: boolean; skeleton?: ReactNode; children: ReactNode }) {
  return loading ? <>{skeleton ?? <PageSkeleton />}</> : <>{children}</>
}
