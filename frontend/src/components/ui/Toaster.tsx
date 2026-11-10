import { useToastStore } from "../../stores/toastStore"
import { Icon } from "./Icon"
import "./motion.css"

/** Pilha de avisos no canto (não bloqueia a tela). Sucesso/progresso usam
 * role="status" (aria-live polite); erro usa role="alert" e só some ao fechar. */
export function Toaster() {
  const { toasts, dismiss } = useToastStore()
  return (
    <div
      className="csp-s-0158"
    >
      {toasts.map((t) => {
        const isError = t.kind === "error"
        return (
          <div
            key={t.id}
            className="toast-in"
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
            <span className="csp-s-0159">{t.text}{(t.count ?? 1) > 1 ? <> <span className="toast-count" key={t.count}>×{t.count}</span></> : null}</span>
            {t.action ? (
              <button
                type="button"
                className="toast-action"
                onClick={() => { t.action?.onClick(); dismiss(t.id) }}
              >
                {t.action.label}
              </button>
            ) : null}
            {t.kind !== "loading" ? (
              <button
                type="button"
                onClick={() => dismiss(t.id)}
                aria-label="Fechar aviso"
                className="csp-s-0160"
              >
                <Icon name="x" size={16} />
              </button>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}
