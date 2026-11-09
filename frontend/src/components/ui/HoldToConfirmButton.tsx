import { useCallback, useEffect, useRef, useState } from "react"
import type { KeyboardEvent, PointerEvent } from "react"
import { prefersReducedMotion } from "../../lib/motion"
import "./holdToConfirm.css"

export const HOLD_MS = 700

interface HoldToConfirmButtonProps {
  label: string
  busyLabel: string
  loading?: boolean
  onConfirm: () => void
}

/**
 * Botão destrutivo "segure para confirmar": protege contra toque acidental sem outro diálogo.
 * Mouse/toque: segurar {HOLD_MS} ms enche o anel. Teclado e leitor de tela: Enter/Espaço confirmam
 * de imediato (ação deliberada, não há clique acidental), então a função nunca depende de segurar.
 */
export function HoldToConfirmButton({ label, busyLabel, loading = false, onConfirm }: HoldToConfirmButtonProps) {
  const [holding, setHolding] = useState(false)
  const timer = useRef<number | null>(null)
  const fired = useRef(false)

  const cancel = useCallback(() => {
    if (timer.current !== null) window.clearTimeout(timer.current)
    timer.current = null
    setHolding(false)
  }, [])

  useEffect(() => cancel, [cancel])

  const start = (event: PointerEvent<HTMLButtonElement>) => {
    if (loading || event.button > 0) return
    fired.current = false
    setHolding(true)
    timer.current = window.setTimeout(() => {
      timer.current = null
      fired.current = true
      setHolding(false)
      onConfirm()
    }, HOLD_MS)
  }

  const keyConfirm = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (loading || (event.key !== "Enter" && event.key !== " ")) return
    event.preventDefault()
    onConfirm()
  }

  return (
    <button
      type="button"
      className={`hold-confirm${holding ? " is-holding" : ""}${prefersReducedMotion() ? " is-static" : ""}`}
      style={{ "--hold-ms": `${HOLD_MS}ms` } as React.CSSProperties}
      disabled={loading}
      aria-busy={loading}
      onPointerDown={start}
      onPointerUp={cancel}
      onPointerLeave={cancel}
      onPointerCancel={cancel}
      onKeyDown={keyConfirm}
      onClick={(event) => {
        // Clique sintético (leitor de tela, "ativar" por voz): detail 0, sem ponteiro. Confirma direto.
        if (event.detail === 0 && !loading && !fired.current) onConfirm()
      }}
    >
      <span className="hold-confirm__fill" aria-hidden="true" />
      <span className="hold-confirm__text">{loading ? busyLabel : holding ? "Continue segurando…" : `${label} (segure)`}</span>
    </button>
  )
}
