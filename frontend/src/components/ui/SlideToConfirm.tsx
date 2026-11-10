import { useCallback, useRef, useState } from "react"
import type { CSSProperties, KeyboardEvent, PointerEvent } from "react"
import { Icon } from "./Icon"
import "./slideToConfirm.css"

/** Fração do trilho que precisa ser percorrida para confirmar. */
export const SLIDE_CONFIRM_THRESHOLD = 0.92

interface SlideToConfirmProps {
  label: string
  busyLabel?: string
  disabled?: boolean
  loading?: boolean
  onConfirm: () => void
}

/**
 * "Deslize para confirmar": protege ações de peso (ativar campanha) contra toque acidental.
 * Mouse/toque: arrastar a alça até o fim. Teclado e leitor de tela: a alça é um botão —
 * Enter/Espaço (ou clique sintético) confirmam direto, então nada depende de arrastar.
 */
export function SlideToConfirm({ label, busyLabel = "Ativando…", disabled = false, loading = false, onConfirm }: SlideToConfirmProps) {
  const trackRef = useRef<HTMLDivElement>(null)
  const drag = useRef<{ startX: number; max: number; pointerId: number } | null>(null)
  const justDragged = useRef(false)
  const [progress, setProgress] = useState(0)
  const [dragging, setDragging] = useState(false)
  const inactive = disabled || loading

  const finish = useCallback((ratio: number) => {
    drag.current = null
    setDragging(false)
    if (ratio >= SLIDE_CONFIRM_THRESHOLD) {
      setProgress(1)
      onConfirm()
      // volta ao início depois do envio; se ainda estiver carregando, o texto muda
      window.setTimeout(() => setProgress(0), 600)
    } else {
      setProgress(0)
    }
  }, [onConfirm])

  const onDown = (event: PointerEvent<HTMLButtonElement>) => {
    if (inactive || event.button > 0 || !trackRef.current) return
    const thumb = event.currentTarget
    const max = trackRef.current.clientWidth - thumb.offsetWidth - 8
    if (max <= 0) return
    drag.current = { startX: event.clientX, max, pointerId: event.pointerId }
    thumb.setPointerCapture(event.pointerId)
    justDragged.current = false
    setDragging(true)
  }
  const onMove = (event: PointerEvent<HTMLButtonElement>) => {
    const d = drag.current
    if (!d) return
    const dx = Math.max(0, Math.min(d.max, event.clientX - d.startX))
    if (dx > 4) justDragged.current = true
    setProgress(dx / d.max)
  }
  const onUp = (event: PointerEvent<HTMLButtonElement>) => {
    const d = drag.current
    if (!d) return
    const dx = Math.max(0, Math.min(d.max, event.clientX - d.startX))
    finish(dx / d.max)
  }
  const onKey = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (inactive || (event.key !== "Enter" && event.key !== " ")) return
    event.preventDefault()
    onConfirm()
  }

  return (
    <div
      ref={trackRef}
      className={`slide-confirm${dragging ? " is-dragging" : ""}${inactive ? " is-disabled" : ""}${loading ? " is-loading" : ""}`}
      style={{ "--slide": progress } as CSSProperties}
    >
      <span className="slide-confirm__fill" aria-hidden="true" />
      <span className="slide-confirm__text" aria-hidden="true">{loading ? busyLabel : `${label} — deslize →`}</span>
      <button
        type="button"
        className="slide-confirm__thumb"
        aria-label={label}
        aria-busy={loading}
        disabled={inactive}
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerCancel={() => { drag.current = null; setDragging(false); setProgress(0) }}
        onKeyDown={onKey}
        onClick={(event) => {
          // Clique sintético (leitor de tela, "ativar" por voz): detail 0, sem ponteiro.
          if (event.detail === 0 && !inactive && !justDragged.current) onConfirm()
        }}
      >
        <Icon name={loading ? "loader-2" : "chevrons-right"} size={20} className={loading ? "animate-spin" : undefined} />
      </button>
    </div>
  )
}
