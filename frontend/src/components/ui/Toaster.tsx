import { useToastStore } from "../../stores/toastStore"
import { Icon } from "./Icon"

/** Pilha de avisos no canto (não bloqueia a tela). Sucesso/progresso usam
 * role="status" (aria-live polite); erro usa role="alert" e só some ao fechar. */
export function Toaster() {
  const { toasts, dismiss } = useToastStore()
  return (
    <div
      style={{
        position: "fixed",
        right: 16,
        bottom: 16,
        left: 16,
        zIndex: 1000,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-end",
        gap: 8,
        pointerEvents: "none",
      }}
    >
      {toasts.map((t) => {
        const isError = t.kind === "error"
        return (
          <div
            key={t.id}
            role={isError ? "alert" : "status"}
            aria-live={isError ? "assertive" : "polite"}
            style={{
              pointerEvents: "auto",
              maxWidth: 420,
              width: "100%",
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "10px 12px",
              borderRadius: "var(--r-md)",
              boxShadow: "var(--shadow-float)",
              font: "var(--fw-medium) var(--fs-body)/1.3 var(--font-sans)",
              background: isError ? "var(--negative-on-glass)" : t.kind === "success" ? "var(--positive-on-glass)" : "var(--surface-elevated)",
              color: isError ? "var(--negative-ink)" : t.kind === "success" ? "var(--black)" : "var(--text-body)",
            }}
          >
            <Icon
              name={t.kind === "loading" ? "loader-2" : isError ? "x-circle" : "check-circle-2"}
              size={16}
              className={t.kind === "loading" ? "animate-spin" : undefined}
            />
            <span style={{ flex: 1, overflowWrap: "anywhere" }}>{t.text}</span>
            {t.kind !== "loading" ? (
              <button
                type="button"
                onClick={() => dismiss(t.id)}
                aria-label="Fechar aviso"
                style={{ minHeight: 32, minWidth: 32, background: "transparent", border: 0, color: "inherit", cursor: "pointer", fontSize: 18 }}
              >
                ×
              </button>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}
