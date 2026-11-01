import { Icon } from "../components/ui/Icon"
import { Panel } from "../components/ui/Panel"

/**
 * Placeholder visual para a futura automação de postagens.
 * Nenhuma execução, configuração ou agendamento automático é iniciado aqui.
 */
export function PostsAutomationPage() {
  return (
    <div className="csp-s-0314">
      <h1 className="csp-s-0315">Automação de posts</h1>

      <Panel
        surface="dark"
        padding={32}
        style={{
          minHeight: 280,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 16,
          textAlign: "center",
        }}
      >
        <span
          aria-hidden="true"
          style={{
            display: "grid",
            placeItems: "center",
            width: 64,
            height: 64,
            borderRadius: "var(--r-lg)",
            color: "var(--sky-400)",
            background: "rgba(129, 189, 250, .08)",
            border: "1px solid var(--border-card)",
          }}
        >
          <Icon name="workflow" size={30} />
        </span>

        <p style={{ margin: 0, font: "var(--text-role-title)", color: "var(--text-body)" }}>
          Automação de posts em breve
        </p>
      </Panel>
    </div>
  )
}
