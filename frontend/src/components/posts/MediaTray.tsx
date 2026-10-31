// Bandeja de fotos do carrossel/álbum: tira horizontal de altura fixa, a ordem
// mostrada é a ordem enviada. Arrastar (HTML5) ou ◀ ▶ reordenam.
import { useEffect, useState } from "react"

export interface TrayItem {
  file: File
  /** índice real em pendingFiles (a bandeja só lista imagens). */
  index: number
}

interface Props {
  items: TrayItem[]
  limit?: number
  notes: string[]
  onMove: (fromIndex: number, toIndex: number) => void
  onRemove: (index: number) => void
}

const caption = "var(--fw-regular) var(--fs-caption)/1.4 var(--font-sans)"

const smallBtn = {
  width: 28,
  height: 28,
  padding: 0,
  borderRadius: "var(--r-sm)",
  border: "1px solid var(--border-hairline)",
  background: "var(--surface-inset)",
  color: "var(--text-body)",
  cursor: "pointer",
  font: caption,
}

export function MediaTray({ items, limit, notes, onMove, onRemove }: Props) {
  const [urls, setUrls] = useState<string[]>([])
  const [dragFrom, setDragFrom] = useState<number | null>(null)

  useEffect(() => {
    const next = items.map((i) => URL.createObjectURL(i.file))
    setUrls(next)
    return () => next.forEach((u) => URL.revokeObjectURL(u))
  }, [items.map((i) => `${i.file.name}:${i.file.size}:${i.file.lastModified}`).join("|")]) // eslint-disable-line react-hooks/exhaustive-deps

  const over = limit != null && items.length > limit

  return (
    <div className="csp-s-0024">
      <div style={{ display: "flex", justifyContent: "space-between", font: caption, color: "var(--text-muted)" }}>
        <span>Fotos do carrossel/álbum</span>
        <span aria-live="polite" style={{ color: over ? "var(--negative)" : undefined }}>
          {items.length}{limit != null ? `/${limit}` : ""}
        </span>
      </div>
      <ul
        aria-label="Fotos na ordem de envio"
        className="csp-s-0025"
      >
        {items.map((item, pos) => (
          <li
            key={`${item.file.name}-${item.file.size}-${pos}`}
            draggable
            onDragStart={() => setDragFrom(pos)}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              if (dragFrom != null && dragFrom !== pos) onMove(items[dragFrom].index, item.index)
              setDragFrom(null)
            }}
            onDragEnd={() => setDragFrom(null)}
            style={{ flex: "0 0 auto", width: 76, display: "flex", flexDirection: "column", gap: 4, opacity: dragFrom === pos ? 0.5 : 1, cursor: "grab" }}
          >
            <div className="csp-s-0026">
              {urls[pos] && <img src={urls[pos]} alt={`Foto ${pos + 1}: ${item.file.name}`} draggable={false} className="csp-s-0027" />}
              <span style={{ position: "absolute", top: 2, left: 2, minWidth: 18, padding: "1px 5px", borderRadius: "var(--r-sm)", background: "rgba(0,0,0,.7)", color: "#fff", font: caption, textAlign: "center" }}>
                {pos + 1}
              </span>
            </div>
            <div className="csp-s-0028">
              <button type="button" aria-label={`Mover foto ${pos + 1} para antes`} disabled={pos === 0} onClick={() => onMove(item.index, items[pos - 1].index)} style={{ ...smallBtn, opacity: pos === 0 ? 0.4 : 1 }}>◀</button>
              <button type="button" aria-label={`Remover foto ${pos + 1}`} onClick={() => onRemove(item.index)} style={{ ...smallBtn, color: "var(--red-300)" }}>✕</button>
              <button type="button" aria-label={`Mover foto ${pos + 1} para depois`} disabled={pos === items.length - 1} onClick={() => onMove(item.index, items[pos + 1].index)} style={{ ...smallBtn, opacity: pos === items.length - 1 ? 0.4 : 1 }}>▶</button>
            </div>
          </li>
        ))}
        {items.length < 2 && (
          <li style={{ flex: "1 0 120px", alignSelf: "center", font: caption, color: "var(--text-muted)" }}>
            Escolha mais fotos acima.
          </li>
        )}
      </ul>
      {notes.map((n) => (
        <span key={n} style={{ font: caption, color: "var(--text-muted)" }}>{n}</span>
      ))}
    </div>
  )
}
