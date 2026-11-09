import { campaignPageWindow } from "../../lib/campaignPagination"

export function CampaignPagination({ page, pageCount, onChange, label }: {
  page: number
  pageCount: number
  onChange: (page: number) => void
  label: string
}) {
  if (pageCount <= 1) return null
  return (
    <nav className="campaign-pagination" aria-label={label}>
      <button type="button" aria-label="Página anterior" disabled={page <= 1}
        onClick={() => onChange(page - 1)}>←</button>
      {campaignPageWindow(page, pageCount).map((item, index) => item === "…"
        ? <span key={`gap-${index}`} aria-hidden="true">…</span>
        : <button key={item} type="button" aria-current={page === item ? "page" : undefined}
          className={page === item ? "is-active" : ""} onClick={() => onChange(item)}>{item}</button>)}
      <button type="button" aria-label="Próxima página" disabled={page >= pageCount}
        onClick={() => onChange(page + 1)}>→</button>
    </nav>
  )
}
