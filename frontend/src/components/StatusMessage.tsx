import type { ReactNode } from "react"

interface StatusMessageProps {
  kind: "error" | "success"
  children: ReactNode
  onDismiss?: () => void
}

/** Feedback inline: erro = role="alert", sucesso = role="status" (aria-live). */
export function StatusMessage({ kind, children, onDismiss }: StatusMessageProps) {
  const isError = kind === "error"
  return (
    <div
      role={isError ? "alert" : "status"}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 12,
        padding: "12px 16px",
        borderRadius: "var(--r-md)",
        font: "var(--fw-medium) var(--fs-body)/1.3 var(--font-sans)",
        background: isError ? "var(--negative-on-glass)" : "var(--positive-on-glass)",
        color: isError ? "var(--negative-ink)" : "var(--black)",
      }}
    >
      <span>{children}</span>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dispensar mensagem"
          className="csp-s-0001"
        >
          ×
        </button>
      )}
    </div>
  )
}
