import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { adminAiCredentialsApi, AI_PROVIDERS, type AiProvider } from "../../api/credentials"
import { formDraftKey, clearFormDraft } from "../../lib/formDraftStorage"
import { useAutosavedDraft } from "../../hooks/useAutosavedDraft"
import { useAuthStore } from "../../stores/authStore"
import { Panel } from "../ui/Panel"
import { Button } from "../ui/Button"
import { Select } from "../ui/Select"
import { TextInput } from "../ui/TextInput"
import { StatusBadge } from "../ui/StatusBadge"
import { ConnectionLight } from "../ui/ConnectionLight"

type Banner = { ok: boolean; text: string } | null

/** Somente tela ADMIN. O segredo é enviado uma vez por HTTPS e jamais reexibido. */
export function AdminAiCredentialCard({
  setBanner,
  onAuthError,
}: {
  setBanner: (banner: Banner) => void
  onAuthError: (error: Error) => void
}) {
  const client = useQueryClient()
  const userId = useAuthStore((state) => state.user?.id)
  const [provider, setProvider] = useState<AiProvider>("gemini")
  const [apiKey, setApiKey] = useState("")
  const [model, setModel] = useState("")
  const draftKey = formDraftKey(userId, "admin-ai-provider-preferences", null, false)
  useAutosavedDraft(draftKey, { provider, model }, (saved) => {
    setProvider(saved?.provider && AI_PROVIDERS.some((item) => item.key === saved.provider) ? saved.provider : "gemini")
    setModel(typeof saved?.model === "string" ? saved.model : "")
    setApiKey("") // NUNCA persistir segredos no navegador.
  })

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin", "ai"],
    queryFn: adminAiCredentialsApi.list,
    refetchInterval: (query) => Object.values(query.state.data?.providers ?? {}).some(
      status => status.state === "testing"
    ) ? 1500 : false,
  })
  const details = AI_PROVIDERS.find((item) => item.key === provider)!
  const status = data?.providers[provider]
  const refresh = () => void client.invalidateQueries({ queryKey: ["admin", "ai"] })

  const saveMutation = useMutation({
    mutationFn: () => adminAiCredentialsApi.save(provider, apiKey, model.trim()),
    onSuccess: () => {
      clearFormDraft(draftKey)
      setApiKey("")
      setModel("")
      setBanner({ ok: true, text: `Chave da plataforma (${details.label}) salva e ativada. Testando conexão…` })
      refresh()
    },
    onError: onAuthError,
  })
  const deleteMutation = useMutation({
    mutationFn: () => adminAiCredentialsApi.delete(provider),
    onSuccess: () => {
      setBanner({ ok: true, text: `${details.label} desconectado da plataforma.` })
      refresh()
    },
    onError: onAuthError,
  })
  const testMutation = useMutation({
    mutationFn: () => adminAiCredentialsApi.test(provider),
    onSuccess: (result) => {
      setBanner({ ok: result.light === "green", text: `${details.label}: ${result.message}` })
      refresh()
    },
    onError: onAuthError,
  })
  const activateMutation = useMutation({
    mutationFn: () => adminAiCredentialsApi.activate(provider),
    onSuccess: () => {
      setBanner({ ok: true, text: `${details.label} ativado para todos os usuários.` })
      refresh()
    },
    onError: onAuthError,
  })

  return (
    <Panel surface="dark" className="cred-card">
      <div className="csp-s-0192">
        <div className="csp-s-0193">
          <h2 className="csp-s-0194">Inteligência Artificial — serviço da plataforma</h2>
          {data?.active && <StatusBadge tone="positive">Em uso: {AI_PROVIDERS.find(item => item.key === data.active)?.label}</StatusBadge>}
        </div>
      </div>
      <p className="csp-s-0211">
        Esta chave é compartilhada por todos os usuários. O consumo é cobrado na conta da plataforma.
        Configure limites de gastos e cotas no provedor. Nenhum cliente terá acesso ao segredo.
      </p>
      {isLoading ? <p role="status">Carregando configuração de IA…</p> : isError ? (
        <div role="alert">
          Não foi possível consultar as chaves da plataforma.
          <Button type="button" variant="ghost" onClick={() => { void refetch() }}>Tentar novamente</Button>
        </div>
      ) : (
        <form
          className="csp-s-0210"
          onSubmit={(event) => { event.preventDefault(); saveMutation.mutate() }}
        >
          <Select
            label="Provedor"
            value={provider}
            onChange={(event) => setProvider(event.target.value as AiProvider)}
            options={AI_PROVIDERS.map((item) => ({
              value: item.key,
              label: data?.providers[item.key]?.connected ? `${item.label} (salva)` : item.label,
            }))}
          />
          <a href={details.helpUrl} target="_blank" rel="noreferrer" className="csp-s-0212">
            Como obter a chave da {details.label} ↗
          </a>
          <div className="csp-s-0209" aria-live="polite">
            <ConnectionLight state={status?.light ?? "red"} />
            <StatusBadge tone={status?.light === "green" ? "positive" : "neutral"}>
              {status?.status_text ?? "Não configurado"}
            </StatusBadge>
            {status?.checked_at && <span className="csp-s-0196">Testado em {new Date(status.checked_at).toLocaleString("pt-BR")}</span>}
          </div>
          <div className="csp-named-field-grid">
            <TextInput
              label="Chave de API"
              type="password"
              autoComplete="off"
              required
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder={status?.connected ? "Salva — cole uma nova para trocar" : "Cole sua chave"}
            />
            <TextInput
              label="Modelo (opcional)"
              autoComplete="off"
              value={model}
              onChange={(event) => setModel(event.target.value)}
              placeholder={status?.model || status?.default_model || "padrão"}
            />
          </div>
          <div className="csp-s-0213">
            {status?.connected && (
              <>
                <Button type="button" variant="ghost" disabled={testMutation.isPending || status?.state === "testing"}
                  onClick={() => testMutation.mutate()}>
                  {testMutation.isPending || status.state === "testing" ? "Testando…" : "Testar conexão"}
                </Button>
                {data?.active !== provider && (
                  <Button type="button" variant="secondary" disabled={activateMutation.isPending}
                    onClick={() => activateMutation.mutate()}>
                    {activateMutation.isPending ? "Ativando…" : "Ativar provedor"}
                  </Button>
                )}
                <Button type="button" variant="ghost" disabled={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate()}>
                  {deleteMutation.isPending ? "Removendo…" : "Desconectar"}
                </Button>
              </>
            )}
            <Button type="submit" variant="primary" disabled={saveMutation.isPending || !apiKey.trim()}>
              {saveMutation.isPending ? "Salvando…" : "Salvar"}
            </Button>
          </div>
        </form>
      )}
    </Panel>
  )
}
