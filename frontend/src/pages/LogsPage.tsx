import { formatInstant } from "../lib/userTimeZone"
import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { logsApi } from "../api/logs"
import { useAuthStore } from "../stores/authStore"
import { formDraftKey } from "../lib/formDraftStorage"
import { useAutosavedDraft } from "../hooks/useAutosavedDraft"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { Badge } from "../components/ui/Badge"
import { TextInput } from "../components/ui/TextInput"
import { PageSkeleton, PageState } from "../components/ui/Skeleton"

const PAGE_SIZE = 50

// ~10 linhas visiveis (cabecalho ~40px + 10 x ~46px); o resto rola dentro do painel.
const TABLE_MAX_HEIGHT = 500

export default function LogsPage() {
  const [offset, setOffset] = useState(0)
  const [statusCode, setStatusCode] = useState("")
  const accountId = useAuthStore((state) => state.user?.id)
  useAutosavedDraft(formDraftKey(accountId, "logs-filters", null, false), { statusCode }, (saved) => {
    setStatusCode(typeof saved?.statusCode === "string" ? saved.statusCode : "")
    setOffset(0)
  })

  const { data, isLoading, error } = useQuery({
    queryKey: ["logs", offset, statusCode],
    queryFn: () =>
      logsApi.list({
        limit: PAGE_SIZE,
        offset,
        status_code: statusCode ? Number(statusCode) : undefined,
      }),
  })

  const rows = data?.data ?? []
  const total = data?.total ?? 0
  const hasNextPage = offset + PAGE_SIZE < total

  const applyFilters = () => setOffset(0)

  return (
    <div className="csp-s-0297">
      <div>
        <h1 className="csp-s-0298">Logs</h1>
        <p className="csp-s-0299">
          Histórico operacional sem identidades, parâmetros de rota ou diagnósticos em texto livre.
        </p>
      </div>

      <Panel surface="dark" style={{ padding: 16 }}>
        <div className="csp-s-0300">
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
          className="csp-s-0301"
        >
          {(error as Error).message}
        </div>
      )}

      <PageState loading={isLoading} skeleton={<PageSkeleton variant="table" heading={false} />}>
      {rows.length === 0 ? (
        <Panel surface="dark" style={{ padding: "48px 16px", textAlign: "center" }}>
          <p className="csp-s-0302">Nenhum log encontrado.</p>
        </Panel>
      ) : (
        <Panel surface="dark" style={{ padding: 0, overflow: "auto", maxHeight: TABLE_MAX_HEIGHT }}>
          <table className="csp-s-0303">
            <thead>
              <tr className="csp-s-0304">
                <th className="csp-named-sticky-th">Timestamp</th>
                <th className="csp-named-sticky-th">Ação / rota</th>
                <th className="csp-named-sticky-th">Status</th>
                <th className="csp-named-sticky-th">Duração</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={`${row.created_at}:${index}`} className="csp-s-0305">
                  <td className="csp-s-0306">
                    {formatInstant(row.created_at)}
                  </td>
                  <td className="csp-s-0307">{row.method} {row.path}</td>
                  <td className="csp-s-0308">
                    {row.status_code ? (
                      <Badge tone={row.status_code >= 400 ? "outline" : "mint"}>{row.status_code}</Badge>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="csp-s-0309">
                    {row.duration_ms != null ? `${row.duration_ms}ms` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}
      </PageState>

      <div className="csp-s-0310">
        <span className="csp-s-0311">
          {total > 0 ? `${offset + 1}–${Math.min(offset + PAGE_SIZE, total)} de ${total}` : null}
        </span>
        <div className="csp-s-0312">
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
