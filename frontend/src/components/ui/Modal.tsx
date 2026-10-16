// Extrapolação: não existe no design system original (ver readme.md → Caveats: "modals").
// Estilo inferido: scrim escuro rgba(0,0,0,.6) + var(--blur-scrim) atrás de um Panel
// centralizado. Usa surface="dark" em vez de "glass" — texto de formulário (labels,
// valores digitados) sobre o gradiente glass real fica raso demais em contraste pra
// confiar num input; "dark" já é o card flat (var(--surface-card)) usado em Transactions/
// Summary, com texto var(--text-body) a 88% de opacidade, mais seguro pra conteúdo denso.
// Botão de fechar é o IconButton icon="x" pedido. Motivado pelos modais de criar/editar e
// confirmar remoção em ProductsPage, PostsPage, ListasPage, CredentialsPage (banner à parte)
// e UsersPage.
import type { ReactNode, CSSProperties } from "react"
import { useEffect, useId, useRef } from "react"
import { createPortal } from "react-dom"
import { Panel } from "./Panel"
import { IconButton } from "./IconButton"

export interface ModalProps {
  open: boolean
  onClose: () => void
  title?: ReactNode
  children?: ReactNode
  width?: number | string
  className?: string
  style?: CSSProperties
}

/** Centered dialog over a dark scrim. Click outside or the "x" to close. */
export function Modal({ open, onClose, title, children, width = 480, className = "", style }: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  useEffect(() => {
    const dialog = dialogRef.current
    if (!open || !dialog) return
    const previouslyFocused = document.activeElement as HTMLElement | null
    dialog.showModal()
    return () => {
      if (dialog.open) dialog.close()
      if (previouslyFocused?.isConnected) previouslyFocused.focus({ preventScroll: true })
    }
  }, [open])
  if (!open) return null
  return createPortal(
    <dialog
      ref={dialogRef}
      className="app-modal"
      aria-labelledby={title ? titleId : undefined}
      aria-label={title ? undefined : "Janela"}
      onCancel={event => { event.preventDefault(); onClose() }}
      onClick={event => { if (event.target === event.currentTarget) onClose() }}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        width: "100vw",
        height: "100dvh",
        maxWidth: "none",
        maxHeight: "none",
        margin: 0,
        border: 0,
        color: "var(--text-body)",
        padding: 16,
        background: "rgba(0,0,0,.6)",
        backdropFilter: "var(--blur-scrim)",
      }}
    >
      <div onClick={(e) => e.stopPropagation()} style={{ width, maxWidth: "100%" }}>
        <Panel
          surface="dark"
          overflowHidden={false}
          className={className}
          style={{ maxHeight: "90vh", overflowY: "auto", ...style }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 10,
              padding: "16px 16px 0",
            }}
          >
            {title ? <span id={titleId} style={{ font: "var(--text-role-title)" }}>{title}</span> : <span />}
            <IconButton icon="x" label="Fechar" tone="plain" size={30} onClick={onClose} />
          </div>
          <div style={{ padding: 16 }}>{children}</div>
        </Panel>
      </div>
    </dialog>,
    document.body,
  )
}
