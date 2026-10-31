import type { ReactNode } from "react"
import { Modal } from "../ui/Modal"
import { Button } from "../ui/Button"

interface ConfirmModalProps {
  title: string
  confirmLabel: string
  busyLabel: string
  loading: boolean
  error?: string | null
  onConfirm: () => void
  onClose: () => void
  children: ReactNode
}

/** Confirmacao destrutiva propria (substitui window.confirm). */
export function ConfirmModal({ title, confirmLabel, busyLabel, loading, error, onConfirm, onClose, children }: ConfirmModalProps) {
  return (
    <Modal open onClose={onClose} title={title} width={420}>
      <div role="alertdialog" aria-label={title} className="csp-s-0083">
        <div className="csp-s-0084">{children}</div>
        {error && (
          <p role="alert" className="csp-s-0085">
            {error}
          </p>
        )}
        <div className="csp-s-0086">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="primary" disabled={loading} onClick={onConfirm} style={{ background: "var(--red-300)" }}>
            {loading ? busyLabel : confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
