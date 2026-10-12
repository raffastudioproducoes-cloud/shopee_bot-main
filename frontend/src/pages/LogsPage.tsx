import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { useAuthStore } from "../stores/authStore"
import { logsApi } from "../api/logs"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { Badge } from "../components/ui/Badge"
import { TextInput } from "../components/ui/TextInput"

const PAGE_SIZE = 50

// ~10 linhas visiveis (cabecalho ~40px + 10 x ~46px); o resto rola dentro do painel.
const TABLE_MAX_HEIGHT = 500
const STICKY_TH = { padding: "10px 16px", position: "sticky", top: 0, zIndex: 1, background: "var(--surface-card)", boxShadow: "inset 0 -1px 0 var(--border-hairline)" } as const

export default function LogsPage() {
  const { user } = useAuthStore()
  const [offset, setOffset] = useState(0)
  const [username, setUsername] = useState("")
  const [statusCode, setStatusCode] = useState("")

  const { data, isLoading, error } = useQuery({
    queryKey: ["logs", offset, username, statusCode],
    queryFn: () =>
      logsApi.list({
        limit: PAGE_SIZE,
        offset,
        username: username || undefined,
        status_code: statusCode ? Number(statusCode) : undefined,
      }),
    enabled: user?.access === "ADMIN",
  })

  if (user?.access !== "ADMIN") {
    return (
      <div style={{ textAlign: "center", padding: "48px 0", color: "var(--text-muted)" }}>
        Você não tem acesso a esta página.
      </div>
    )
  }

  const rows = data?.data ?? []
  const total = data?.total ?? 0
  const hasNextPage = offset + PAGE_SIZE < total

  const applyFilters = () => setOffset(0)

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap-column)" }}>
      <div>
        <h1 style={{ font: "var(--text-role-hero)", color: "var(--text-display)", margin: 0 }}>Logs</h1>
        <p style={{ color: "var(--text-muted)", marginTop: 4 }}>
          Histórico de requisições e passos de negócio (senhas e tokens nunca aparecem aqui).
        </p>
      </div>

      <Panel surface="dark" style={{ padding: 16 }}>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
          <TextInput
            label="Usuário"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="username"
          />
          <TextInput
            label="Status code"
            value={statusCode}
            onChange={(e) => setStatusCode(e.target.value)}
            placeholder="200"
            type="number"
          />
          <Button variant="secondary" onClick={applyFilters}>
            Filtrar
          </Button>
        </div>
      </Panel>

      {error && (
        <div
          style={{
            padding: "12px 16px",
            borderRadius: "var(--r-md)",
            font: "var(--fw-medium) var(--fs-body)/1.3 var(--font-sans)",
            background: "var(--negative-on-glass)",
            color: "var(--negative-ink)",
          }}
        >
          {(error as Error).message}
        </div>
      )}

      {isLoading ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 256, color: "var(--text-muted)" }}>
          Carregando...
        </div>
      ) : rows.length === 0 ? (
        <Panel surface="dark" style={{ padding: "48px 16px", textAlign: "center" }}>
          <p style={{ color: "var(--text-muted)", font: "var(--text-role-body)", margin: 0 }}>Nenhum log encontrado.</p>
        </Panel>
      ) : (
        <Panel surface="dark" style={{ padding: 0, overflow: "auto", maxHeight: TABLE_MAX_HEIGHT }}>
          <table style={{ width: "100%", minWidth: 760, borderCollapse: "collapse", font: "var(--fw-regular) var(--fs-body)/1.3 var(--font-sans)" }}>
            <thead>
              <tr style={{ textAlign: "left", color: "var(--text-muted)" }}>
                <th style={STICKY_TH}>Timestamp</th>
                <th style={STICKY_TH}>Usuário</th>
                <th style={STICKY_TH}>Ação / rota</th>
                <th style={STICKY_TH}>Status</th>
                <th style={STICKY_TH}>Duração</th>
                <th style={STICKY_TH}>Erro</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} style={{ borderBottom: "1px solid var(--border-hairline)" }}>
                  <td style={{ padding: "10px 16px", whiteSpace: "nowrap", color: "var(--text-muted)" }}>
                    {new Date(row.created_at).toLocaleString("pt-BR")}
                  </td>
                  <td style={{ padding: "10px 16px" }}>{row.username ?? "—"}</td>
                  <td style={{ padding: "10px 16px" }}>{row.action ?? `${row.method} ${row.path}`}</td>
                  <td style={{ padding: "10px 16px" }}>
                    {row.status_code ? (
                      <Badge tone={row.status_code >= 400 ? "outline" : "mint"}>{row.status_code}</Badge>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td style={{ padding: "10px 16px", color: "var(--text-muted)" }}>
                    {row.duration_ms != null ? `${row.duration_ms}ms` : "—"}
                  </td>
                  <td style={{ padding: "10px 16px", color: "var(--negative-ink)", maxWidth: 320 }}>
                    {row.error ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ color: "var(--text-muted)", font: "var(--fs-small)" }}>
          {total > 0 ? `${offset + 1}–${Math.min(offset + PAGE_SIZE, total)} de ${total}` : null}
        </span>
        <div style={{ display: "flex", gap: 8 }}>
          <Button variant="ghost" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
            Anterior
          </Button>
          <Button variant="ghost" disabled={!hasNextPage} onClick={() => setOffset(offset + PAGE_SIZE)}>
            Próxima
          </Button>
        </div>
      </div>
    </div>
  )
}
