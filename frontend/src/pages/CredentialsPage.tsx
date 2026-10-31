import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import {
  credentialsApi,
  aiCredentialsApi,
  AI_PROVIDERS,
  type AiProvider,
  type SimpleNetwork,
  type CredentialStatusWithLight,
} from "../api/credentials"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { Skeleton, SkeletonCard, SkeletonRegion } from "../components/ui/Skeleton"
import { IconButton } from "../components/ui/IconButton"
import { TextInput } from "../components/ui/TextInput"
import { StatusBadge } from "../components/ui/StatusBadge"
import { ConnectionLight } from "../components/ui/ConnectionLight"
import { Icon } from "../components/ui/Icon"
import { Select } from "../components/ui/Select"
import { Modal } from "../components/ui/Modal"
import { isNetworkDisabled } from "../lib/networkLimits"

// X/Facebook saíram daqui: têm card dedicado (XCredentialCard,
// FacebookCredentialCard — mesmo padrão de TikTok/Instagram) porque usam
// OAuth authorize/callback, não app_id/secret por formulário. Kwai também
// saiu do mapeamento: renderizado à parte, por último, com aviso "em breve".
const SIMPLE_NETWORKS: { key: SimpleNetwork; label: string }[] = [
  { key: "shopee", label: "Shopee" },
]

// Grade de 2 colunas que colapsa pra 1 em telas estreitas (mesmo efeito do
// antigo `grid-cols-1 sm:grid-cols-2`, sem depender de breakpoint Tailwind).
type OAuthNetwork = "threads" | "x" | "facebook" | "tiktok" | "instagram"

const OAUTH_CONSENT: Record<OAuthNetwork, { label: string; details: string }> = {
  threads: { label: "Threads", details: "sua identidade no Threads e autorização para publicar posts em seu nome" },
  x: { label: "X", details: "sua identidade no X e autorização para publicar posts em seu nome" },
  facebook: { label: "Facebook", details: "a Página que você administra e autorização para publicar nela em seu nome" },
  tiktok: { label: "TikTok", details: "sua identidade no TikTok e autorização para publicar conteúdo em seu nome" },
  instagram: { label: "Instagram", details: "sua conta Business/Creator e autorização para publicar conteúdo em seu nome" },
}

function OAuthConsentModal({
  network,
  open,
  busy,
  onClose,
  onContinue,
}: {
  network: OAuthNetwork
  open: boolean
  busy: boolean
  onClose: () => void
  onContinue: () => void
}) {
  const consent = OAUTH_CONSENT[network]
  return (
    <Modal open={open} onClose={onClose} title={`Conectar ${consent.label}`}>
      <div className="csp-s-0188">
        <p className="csp-s-0189">
          Você será levado ao {consent.label} para autorizar esta conexão.
        </p>
        <p className="csp-s-0190">
          O Auto Orbital solicitará {consent.details}. A conexão é vinculada somente ao seu perfil ativo e pode ser removida a qualquer momento em “Desconectar”.
        </p>
        <div className="csp-s-0191">
          <Button type="button" variant="ghost" disabled={busy} onClick={onClose}>Cancelar</Button>
          <Button type="button" variant="primary" disabled={busy} onClick={onContinue}>
            {busy ? "Redirecionando..." : `Continuar para ${consent.label}`}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

// ── Card recolhivel: estado por card em localStorage; recolhido mostra so
// titulo + status (o corpo e escondido por CSS, ver .cred-card em index.css). ──

const COLLAPSE_KEY = "credentials-collapsed:"
const CollapseCtx = createContext<{ collapsed: boolean; toggle: () => void }>({ collapsed: false, toggle: () => {} })

function readCollapsed(id: string): boolean {
  try {
    return localStorage.getItem(COLLAPSE_KEY + id) === "1"
  } catch {
    return false
  }
}

function CredPanel({ id, children }: { id: string; children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(() => readCollapsed(id))
  const toggle = () => {
    const next = !collapsed
    setCollapsed(next)
    try {
      localStorage.setItem(COLLAPSE_KEY + id, next ? "1" : "0")
    } catch {
      // sem localStorage: so nao persiste
    }
  }
  return (
    <CollapseCtx.Provider value={{ collapsed, toggle }}>
      <Panel surface="dark" className={collapsed ? "cred-card is-collapsed" : "cred-card"}>
        {children}
      </Panel>
    </CollapseCtx.Provider>
  )
}

function CredHeader({ title, trailing }: { title: ReactNode; trailing?: ReactNode }) {
  const { collapsed, toggle } = useContext(CollapseCtx)
  return (
    <header className="csp-s-0192">
      <div className="csp-s-0193">
        <span className="csp-s-0194">
          {title}
        </span>
        <IconButton
          icon={collapsed ? "chevron-down" : "chevron-up"}
          label={collapsed ? "Expandir card" : "Recolher card"}
          tone="plain"
          size={30}
          aria-expanded={!collapsed}
          onClick={toggle}
          style={{ flexShrink: 0 }}
        />
      </div>
      {trailing}
    </header>
  )
}

const TESTING_POLL_MS = 1500

function anyTesting(map?: Record<string, { state?: string }>): boolean {
  return !!map && Object.values(map).some((s) => s?.state === "testing")
}

// Luz + selo + data do teste, iguais em todos os cards. Em "testing" a luz vira
// um spinner e o selo anuncia "Testando…" (região viva, lida por leitor de tela).
function ConnectionStatus({ status }: { status: CredentialStatusWithLight }) {
  const testing = status.state === "testing"
  return (
    <>
      {testing ? (
        <Icon name="loader-2" size={14} className="animate-spin" style={{ color: "var(--amber-300)", flexShrink: 0 }} />
      ) : (
        <ConnectionLight state={status.light} />
      )}
      <span role="status" aria-live="polite" className="csp-s-0195">
        <StatusBadge
          tone={status.light === "green" ? "positive" : "neutral"}
          icon={testing ? undefined : status.light === "green" ? "check-circle-2" : "x-circle"}
        >
          {status.status_text ?? (status.connected ? "Conectado" : "Desconectado")}
        </StatusBadge>
      </span>
      {status.checked_at && !testing && (
        <span className="csp-s-0196">
          Testado em {new Date(status.checked_at).toLocaleString("pt-BR")}
        </span>
      )}
    </>
  )
}

const EMPTY_STATUS: CredentialStatusWithLight = {
  connected: false,
  light: "red",
  checked_at: null,
  check_message: null,
}

export function CredentialsPage() {
  const { logout } = useAuthStore()
  const queryClient = useQueryClient()
  const [banner, setBanner] = useState<{ ok: boolean; text: string } | null>(null)

  const { data: status, isLoading } = useQuery({
    queryKey: ["credentials"],
    queryFn: () => credentialsApi.list(),
    // Salvar/reconectar dispara teste automático no backend: enquanto algum
    // card estiver "testando", consulta de novo (o backend encerra o estado
    // sozinho em até ~45 s, então o polling nunca fica infinito).
    refetchInterval: (q) => (anyTesting(q.state.data) ? TESTING_POLL_MS : false),
  })

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const threads = params.get("threads")
    if (!threads) return
    setBanner(
      threads === "success"
        ? { ok: true, text: "Threads conectado com sucesso." }
        : { ok: false, text: "Falha ao conectar o Threads. Tente novamente." }
    )
    params.delete("threads")
    const query = params.toString()
    window.history.replaceState(null, "", window.location.pathname + (query ? `?${query}` : ""))
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const tiktok = params.get("tiktok")
    if (!tiktok) return
    setBanner(
      tiktok === "success"
        ? { ok: true, text: "TikTok conectado com sucesso." }
        : { ok: false, text: "Falha ao conectar o TikTok. Tente novamente." }
    )
    params.delete("tiktok")
    const query = params.toString()
    window.history.replaceState(null, "", window.location.pathname + (query ? `?${query}` : ""))
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const instagram = params.get("instagram")
    if (!instagram) return
    setBanner(
      instagram === "success"
        ? { ok: true, text: "Instagram conectado com sucesso." }
        : { ok: false, text: "Falha ao conectar o Instagram. Tente novamente." }
    )
    params.delete("instagram")
    const query = params.toString()
    window.history.replaceState(null, "", window.location.pathname + (query ? `?${query}` : ""))
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const x = params.get("x")
    if (!x) return
    setBanner(
      x === "success"
        ? { ok: true, text: "X conectado com sucesso." }
        : { ok: false, text: "Falha ao conectar o X. Tente novamente." }
    )
    params.delete("x")
    const query = params.toString()
    window.history.replaceState(null, "", window.location.pathname + (query ? `?${query}` : ""))
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const facebook = params.get("facebook")
    if (!facebook) return
    setBanner(
      facebook === "success"
        ? { ok: true, text: "Facebook conectado com sucesso." }
        : { ok: false, text: "Falha ao conectar o Facebook. Tente novamente." }
    )
    params.delete("facebook")
    const query = params.toString()
    window.history.replaceState(null, "", window.location.pathname + (query ? `?${query}` : ""))
  }, [])

  const onAuthError = (err: Error) => {
    if (err.message.includes("401") || err.message === "Não autenticado") {
      logout()
      router.navigate({ to: "/login" })
      return
    }
    // Extrapolação: antes desse fallback, qualquer erro que não fosse 401
    // (ex: 502 do bridge interno na validação da Shopee, 400 de credencial
    // inválida) era descartado em silêncio — o botão voltava de "Salvando..."
    // pra "Salvar" sem nenhum aviso, dando a impressão de que nada aconteceu.
    setBanner({ ok: false, text: err.message || "Erro ao salvar credencial." })
  }

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["credentials"] })

  if (isLoading) {
    return (
      <SkeletonRegion><div className="csp-s-0197"><div><Skeleton width="180px" height={34} /><Skeleton className="skeleton-sub" width="360px" /></div><div className="credentials-card-grid csp-named-card-grid">{[1,2,3,4,5].map(i => <SkeletonCard key={i} />)}</div></div></SkeletonRegion>
    )
  }

  return (
    <div className="csp-s-0198">
      <div>
        <h1 className="csp-s-0199">Credenciais</h1>
        <p className="csp-s-0200">
          O valor da credencial nunca é reexibido depois de salvo — só o status de conexão.
        </p>
      </div>

      {banner && (
        <div
          style={{
            padding: "12px 16px",
            borderRadius: "var(--r-md)",
            font: "var(--fw-medium) var(--fs-body)/1.3 var(--font-sans)",
            background: banner.ok ? "var(--positive-on-glass)" : "var(--negative-on-glass)",
            color: banner.ok ? "var(--positive-ink)" : "var(--negative-ink)",
          }}
        >
          {banner.text}
        </div>
      )}

      {/* Grade responsiva: cards lado a lado no desktop, 1 coluna no celular.
          Um novo card (ex.: chave de IA) entra como mais um filho desta grade. */}
      <div className="credentials-card-grid csp-named-card-grid">
        {SIMPLE_NETWORKS.map((network) => (
          <SimpleCredentialCard
            key={network.key}
            network={network.key}
            label={network.label}
            status={status?.[network.key] ?? EMPTY_STATUS}
            onSaved={invalidate}
            onAuthError={onAuthError}
            setBanner={setBanner}
          />
        ))}

        <AiCredentialCard onAuthError={onAuthError} setBanner={setBanner} />

        <ThreadsCredentialCard
          status={status?.threads ?? EMPTY_STATUS}
          onSaved={invalidate}
          onAuthError={onAuthError}
          setBanner={setBanner}
        />

        <XCredentialCard
          status={status?.x ?? EMPTY_STATUS}
          onSaved={invalidate}
          onAuthError={onAuthError}
          setBanner={setBanner}
        />

        <FacebookCredentialCard
          status={status?.facebook ?? EMPTY_STATUS}
          onSaved={invalidate}
          onAuthError={onAuthError}
          setBanner={setBanner}
        />

        <InstagramCredentialCard
          status={status?.instagram ?? EMPTY_STATUS}
          onSaved={invalidate}
          onAuthError={onAuthError}
          setBanner={setBanner}
        />

        <TikTokCredentialCard
          status={status?.tiktok ?? EMPTY_STATUS}
          onSaved={invalidate}
          onAuthError={onAuthError}
          setBanner={setBanner}
        />

        <SimpleCredentialCard
          network="kwai"
          label="Kwai"
          status={status?.kwai ?? EMPTY_STATUS}
          onSaved={invalidate}
          onAuthError={onAuthError}
          setBanner={setBanner}
          comingSoon
        />
      </div>

    </div>
  )
}

// ── Sinalizador (luz, visível a todo mundo) + botão "Testar conexão". ─────

function CredentialTrailing({
  network,
  label,
  status,
  onSaved,
  onAuthError,
  setBanner,
}: {
  network: SimpleNetwork | "threads"
  label: string
  status: CredentialStatusWithLight
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  const testMutation = useMutation({
    mutationFn: () => credentialsApi.testConnection(network),
    onSuccess: (result) => {
      setBanner({
        ok: result.light === "green",
        text: `${label}: ${result.message || (result.light === "green" ? "conectado" : "problema encontrado")}`,
      })
      onSaved()
    },
    onError: onAuthError,
  })

  return (
    <div className="csp-s-0201">
      <ConnectionStatus status={status} />
      {status.connected && (
        <Button
          type="button"
          variant="ghost"
          disabled={testMutation.isPending || status.state === "testing"}
          onClick={() => testMutation.mutate()}
        >
          {testMutation.isPending || status.state === "testing" ? "Testando..." : "Testar conexão"}
        </Button>
      )}
    </div>
  )
}

// ── Card genérico (Shopee, X, Facebook, Kwai) ────────────────────────────────

function SimpleCredentialCard({
  network,
  label,
  status,
  onSaved,
  onAuthError,
  setBanner,
  comingSoon,
}: {
  network: SimpleNetwork
  label: string
  status: CredentialStatusWithLight
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
  comingSoon?: boolean
}) {
  const [appId, setAppId] = useState("")
  const [secret, setSecret] = useState("")
  const connected = status.connected
  const helpUrl = network === "shopee" ? "https://affiliate.shopee.com.br/" : undefined

  const saveMutation = useMutation({
    mutationFn: () => credentialsApi.save(network, appId, secret),
    onSuccess: () => {
      setAppId("")
      setSecret("")
      setBanner({ ok: true, text: `${label} salvo. Testando a conexão…` })
      onSaved()
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: () => credentialsApi.delete(network),
    onSuccess: () => {
      setBanner({ ok: true, text: `${label} desconectado.` })
      onSaved()
    },
    onError: onAuthError,
  })

  if (comingSoon) {
    return (
      <CredPanel id={label}>
        <CredHeader title={label} />
        <div className="csp-s-0202">
          <p className="csp-s-0203">
            Em breve — a ligação com {label} ainda não está disponível.
          </p>
        </div>
      </CredPanel>
    )
  }

  return (
    <CredPanel id={label}>
      <CredHeader
        title={label}
        trailing={
          <CredentialTrailing
            network={network}
            label={label}
            status={status}
            onSaved={onSaved}
            onAuthError={onAuthError}
            setBanner={setBanner}
          />
        }
      />

      <form
        onSubmit={(e) => {
          e.preventDefault()
          saveMutation.mutate()
        }}
        className="csp-s-0204"
      >
        {helpUrl && (
          <div className="csp-s-0205">
            <a
              href={helpUrl}
              target="_blank"
              rel="noreferrer"
              className="csp-s-0206"
            >
              Abrir Portal de Afiliados da {label} (pegar App ID/Secret) ↗
            </a>
            {network === "shopee" && (
              <button
                type="button"
                aria-label="Ver tutorial de como gerar App ID e Secret na Shopee"
                title="Tutorial Shopee"
                onClick={() => {
                  window.location.href = "/ajuda?tab=shopee"
                }}
                className="csp-s-0207"
              >
                ?
              </button>
            )}
          </div>
        )}
        <div className="csp-named-field-grid">
          <TextInput
            label="App ID"
            value={appId}
            onChange={(e) => setAppId(e.target.value)}
            placeholder="APP ID"
            required
          />
          <TextInput
            label="Secret"
            type="password"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
            placeholder="Secret"
            autoComplete="off"
            required
          />
        </div>
        <div className="csp-s-0208">
          {connected && (
            <Button
              type="button"
              variant="ghost"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
              style={{ color: "var(--red-300)" }}
            >
              {deleteMutation.isPending ? "Removendo..." : "Desconectar"}
            </Button>
          )}
          <Button
            type="submit"
            variant="primary"
            disabled={saveMutation.isPending || !appId || !secret}
          >
            {saveMutation.isPending ? "Salvando..." : "Salvar"}
          </Button>
        </div>
      </form>
    </CredPanel>
  )
}

// ── Card da chave de IA (admin E usuário comum): cada um usa a PRÓPRIA chave
// no "Gerar texto com IA" (Posts). Sem chave global no servidor. ──────────────

function AiCredentialCard({
  onAuthError,
  setBanner,
}: {
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  const queryClient = useQueryClient()
  const [provider, setProvider] = useState<AiProvider>("gemini")
  const [apiKey, setApiKey] = useState("")
  const [model, setModel] = useState("")
  const { data } = useQuery({
    queryKey: ["credentials", "ai"],
    queryFn: () => aiCredentialsApi.list(),
    refetchInterval: (q) => (anyTesting(q.state.data?.providers) ? TESTING_POLL_MS : false),
  })
  const info = AI_PROVIDERS.find((p) => p.key === provider)!
  const status = data?.providers[provider] ?? { ...EMPTY_STATUS, model: null, default_model: "" }
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["credentials", "ai"] })

  const saveMutation = useMutation({
    mutationFn: () => aiCredentialsApi.save(provider, apiKey, model.trim()),
    onSuccess: () => {
      setApiKey("")
      setModel("")
      setBanner({ ok: true, text: `Chave de IA (${info.label}) salva. Testando a conexão…` })
      refresh()
    },
    onError: onAuthError,
  })
  const deleteMutation = useMutation({
    mutationFn: () => aiCredentialsApi.delete(provider),
    onSuccess: () => {
      setBanner({ ok: true, text: `Chave de IA (${info.label}) removida.` })
      refresh()
    },
    onError: onAuthError,
  })
  const testMutation = useMutation({
    mutationFn: () => aiCredentialsApi.test(provider),
    onSuccess: (result) => {
      setBanner({ ok: result.light === "green", text: `${info.label}: ${result.message}` })
      refresh()
    },
    onError: onAuthError,
  })

  return (
    <CredPanel id="Inteligência Artificial">
      <CredHeader
        title="Inteligência Artificial"
        trailing={
          <div className="csp-s-0209">
            <ConnectionStatus status={status} />
            {status.connected && (
              <Button
                type="button"
                variant="ghost"
                disabled={testMutation.isPending || status.state === "testing"}
                onClick={() => testMutation.mutate()}
              >
                {testMutation.isPending || status.state === "testing" ? "Testando..." : "Testar conexão"}
              </Button>
            )}
          </div>
        }
      />
      <form
        onSubmit={(e) => {
          e.preventDefault()
          saveMutation.mutate()
        }}
        className="csp-s-0210"
      >
        <p className="csp-s-0211">
          Usada no "Gerar texto com IA" dos Posts. A chave é sua: o consumo é cobrado na sua conta do provedor.
          {data?.active ? ` Em uso agora: ${AI_PROVIDERS.find((p) => p.key === data.active)?.label}.` : ""}
        </p>
        <Select
          label="Provedor"
          value={provider}
          onChange={(e) => setProvider(e.target.value as AiProvider)}
          options={AI_PROVIDERS.map((p) => ({
            value: p.key,
            label: data?.providers[p.key]?.connected ? `${p.label} (salva)` : p.label,
          }))}
        />
        <a href={info.helpUrl} target="_blank" rel="noreferrer" className="csp-s-0212">
          Como obter a chave da {info.label} ↗
        </a>
        <div className="csp-named-field-grid">
          <TextInput
            label="Chave de API"
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={status.connected ? "Salva — cole uma nova para trocar" : "Cole sua chave"}
            autoComplete="off"
            required
          />
          <TextInput
            label="Modelo (opcional)"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder={status.model || status.default_model || "padrão"}
            autoComplete="off"
          />
        </div>
        <div className="csp-s-0213">
          {status.connected && (
            <Button
              type="button"
              variant="ghost"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
              style={{ color: "var(--red-300)" }}
            >
              {deleteMutation.isPending ? "Removendo..." : "Desconectar"}
            </Button>
          )}
          <Button type="submit" variant="primary" disabled={saveMutation.isPending || !apiKey.trim()}>
            {saveMutation.isPending ? "Salvando..." : "Salvar"}
          </Button>
        </div>
      </form>
    </CredPanel>
  )
}

// ── Card do Threads (OAuth — cola token já emitido) ─────────────────────────────

function ThreadsCredentialCard({
  status,
  onSaved,
  onAuthError,
  setBanner,
}: {
  status: CredentialStatusWithLight
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  const connected = status.connected
  const [consentOpen, setConsentOpen] = useState(false)

  const authorizeMutation = useMutation({
    mutationFn: () => credentialsApi.authorizeThreads(),
    onSuccess: ({ url }) => {
      window.location.href = url
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: () => credentialsApi.deleteThreads(),
    onSuccess: () => {
      setBanner({ ok: true, text: "Threads desconectado." })
      onSaved()
    },
    onError: onAuthError,
  })

  return (
    <CredPanel id="Threads">
      <CredHeader
        title="Threads"
        trailing={
          <CredentialTrailing
            network="threads"
            label="Threads"
            status={status}
            onSaved={onSaved}
            onAuthError={onAuthError}
            setBanner={setBanner}
          />
        }
      />

      <div className="csp-s-0214">
        <p className="csp-s-0215">
          Conecte sua conta do Threads com um clique — nenhuma configuração técnica necessária.
        </p>

        <div className="csp-s-0216">
          <Button
            type="button"
            variant="primary"
            disabled={authorizeMutation.isPending}
            onClick={() => setConsentOpen(true)}
          >
            {authorizeMutation.isPending ? "Conectando..." : "Conectar Threads"}
          </Button>
          {connected && (
            <Button
              type="button"
              variant="ghost"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
              style={{ color: "var(--red-300)" }}
            >
              {deleteMutation.isPending ? "Removendo..." : "Desconectar"}
            </Button>
          )}
        </div>

      </div>
      <OAuthConsentModal
        network="threads"
        open={consentOpen}
        busy={authorizeMutation.isPending}
        onClose={() => setConsentOpen(false)}
        onContinue={() => authorizeMutation.mutate()}
      />
    </CredPanel>
  )
}

// ── Card do X (App ID/Secret + OAuth 2.0/PKCE) ──────────────────────────────────

function XCredentialCard({
  status,
  onSaved,
  onAuthError,
  setBanner,
}: {
  status: CredentialStatusWithLight
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  const connected = status.connected
  const disabledReason = isNetworkDisabled("x")
  const [consentOpen, setConsentOpen] = useState(false)

  const authorizeMutation = useMutation({
    mutationFn: () => credentialsApi.authorizeX(),
    onSuccess: ({ url }) => {
      window.location.href = url
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: () => credentialsApi.delete("x"),
    onSuccess: () => {
      setBanner({ ok: true, text: "X desconectado." })
      onSaved()
    },
    onError: onAuthError,
  })

  return (
    <CredPanel id="X (Twitter)">
      <CredHeader
        title="X (Twitter)"
        trailing={
          <CredentialTrailing
            network="x"
            label="X"
            status={status}
            onSaved={onSaved}
            onAuthError={onAuthError}
            setBanner={setBanner}
          />
        }
      />

      <div className="csp-s-0217">
        <p className="csp-s-0218">
          Conecte sua conta do X com um clique — nenhuma configuração técnica necessária.
        </p>

        <div className="csp-s-0219">
          <Button
            type="button"
            variant="primary"
            disabled={!!disabledReason || authorizeMutation.isPending}
            onClick={() => setConsentOpen(true)}
          >
            {authorizeMutation.isPending ? "Conectando..." : connected ? "Reconectar X" : "Conectar X"}
          </Button>
          {connected && (
            <Button
              type="button"
              variant="ghost"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
              style={{ color: "var(--red-300)" }}
            >
              {deleteMutation.isPending ? "Removendo..." : "Desconectar"}
            </Button>
          )}
        </div>

        {disabledReason && (
          <p role="status" className="csp-s-0220">
            Plano pago em breve; publicação no X pausada.
          </p>
        )}

        {connected && status.missing_scopes?.includes("media.write") && (
          <p role="alert" className="csp-s-0221">
            Reconecte o X para liberar imagens: esta conexão não tem a permissão de enviar mídia.
          </p>
        )}
      </div>
      <OAuthConsentModal
        network="x"
        open={consentOpen}
        busy={authorizeMutation.isPending}
        onClose={() => setConsentOpen(false)}
        onContinue={() => authorizeMutation.mutate()}
      />
    </CredPanel>
  )
}

// ── Card do Facebook (OAuth de app único — clicar "Conectar Facebook") ──────────

function FacebookCredentialCard({
  status,
  onSaved,
  onAuthError,
  setBanner,
}: {
  status: CredentialStatusWithLight
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  const connected = status.connected
  const [consentOpen, setConsentOpen] = useState(false)

  const authorizeMutation = useMutation({
    mutationFn: () => credentialsApi.authorizeFacebook(),
    onSuccess: ({ url }) => {
      window.location.href = url
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: () => credentialsApi.delete("facebook"),
    onSuccess: () => {
      setBanner({ ok: true, text: "Facebook desconectado." })
      onSaved()
    },
    onError: onAuthError,
  })

  return (
    <CredPanel id="Facebook">
      <CredHeader
        title="Facebook"
        trailing={
          <CredentialTrailing
            network="facebook"
            label="Facebook"
            status={status}
            onSaved={onSaved}
            onAuthError={onAuthError}
            setBanner={setBanner}
          />
        }
      />

      <div className="csp-s-0222">
        <p className="csp-s-0223">
          Conecte a Página do Facebook com um clique — nenhuma configuração técnica necessária.
          Se você administra mais de uma Página, a primeira encontrada é conectada automaticamente.
        </p>

        <div className="csp-s-0224">
          <Button
            type="button"
            variant="primary"
            disabled={authorizeMutation.isPending}
            onClick={() => setConsentOpen(true)}
          >
            {authorizeMutation.isPending ? "Conectando..." : connected ? "Reconectar Facebook" : "Conectar Facebook"}
          </Button>
          {connected && (
            <Button
              type="button"
              variant="ghost"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
              style={{ color: "var(--red-300)" }}
            >
              {deleteMutation.isPending ? "Removendo..." : "Desconectar"}
            </Button>
          )}
        </div>

      </div>
      <OAuthConsentModal
        network="facebook"
        open={consentOpen}
        busy={authorizeMutation.isPending}
        onClose={() => setConsentOpen(false)}
        onContinue={() => authorizeMutation.mutate()}
      />
    </CredPanel>
  )
}

// ── Card do TikTok (OAuth de app único — clicar "Conectar TikTok") ──────────────

function TikTokCredentialCard({
  status,
  onSaved,
  onAuthError,
  setBanner,
}: {
  status: CredentialStatusWithLight
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  const connected = status.connected
  const [consentOpen, setConsentOpen] = useState(false)

  const authorizeMutation = useMutation({
    mutationFn: () => credentialsApi.authorizeTiktok(),
    onSuccess: ({ url }) => {
      window.location.href = url
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: () => credentialsApi.delete("tiktok"),
    onSuccess: () => {
      setBanner({ ok: true, text: "TikTok desconectado." })
      onSaved()
    },
    onError: onAuthError,
  })

  return (
    <CredPanel id="TikTok">
      <CredHeader
        title="TikTok"
        trailing={
          <CredentialTrailing
            network="tiktok"
            label="TikTok"
            status={status}
            onSaved={onSaved}
            onAuthError={onAuthError}
            setBanner={setBanner}
          />
        }
      />

      <div className="csp-s-0225">
        <p className="csp-s-0226">
          Conecte sua conta do TikTok com um clique — nenhuma configuração técnica necessária.
        </p>

        <div className="csp-s-0227">
          <Button
            type="button"
            variant="primary"
            disabled={authorizeMutation.isPending}
            onClick={() => setConsentOpen(true)}
          >
            {authorizeMutation.isPending ? "Conectando..." : connected ? "Reconectar TikTok" : "Conectar TikTok"}
          </Button>
          {connected && (
            <Button
              type="button"
              variant="ghost"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
              style={{ color: "var(--red-300)" }}
            >
              {deleteMutation.isPending ? "Removendo..." : "Desconectar"}
            </Button>
          )}
        </div>

      </div>
      <OAuthConsentModal
        network="tiktok"
        open={consentOpen}
        busy={authorizeMutation.isPending}
        onClose={() => setConsentOpen(false)}
        onContinue={() => authorizeMutation.mutate()}
      />
    </CredPanel>
  )
}

// ── Card do Instagram (OAuth de app único via Facebook Login for Business) ─────

function InstagramCredentialCard({
  status,
  onSaved,
  onAuthError,
  setBanner,
}: {
  status: CredentialStatusWithLight
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  const connected = status.connected
  const [consentOpen, setConsentOpen] = useState(false)

  const authorizeMutation = useMutation({
    mutationFn: () => credentialsApi.authorizeInstagram(),
    onSuccess: ({ url }) => {
      window.location.href = url
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: () => credentialsApi.delete("instagram"),
    onSuccess: () => {
      setBanner({ ok: true, text: "Instagram desconectado." })
      onSaved()
    },
    onError: onAuthError,
  })

  return (
    <CredPanel id="Instagram">
      <CredHeader
        title="Instagram"
        trailing={
          <CredentialTrailing
            network="instagram"
            label="Instagram"
            status={status}
            onSaved={onSaved}
            onAuthError={onAuthError}
            setBanner={setBanner}
          />
        }
      />

      <div className="csp-s-0228">
        <p className="csp-s-0229">
          Publicar exige uma conta Business/Creator vinculada a uma Página do Facebook — conecte
          com um clique, nenhuma configuração técnica necessária.
        </p>

        <div className="csp-s-0230">
          <Button
            type="button"
            variant="primary"
            disabled={authorizeMutation.isPending}
            onClick={() => setConsentOpen(true)}
          >
            {authorizeMutation.isPending ? "Conectando..." : connected ? "Reconectar Instagram" : "Conectar Instagram"}
          </Button>
          {connected && (
            <Button
              type="button"
              variant="ghost"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
              style={{ color: "var(--red-300)" }}
            >
              {deleteMutation.isPending ? "Removendo..." : "Desconectar"}
            </Button>
          )}
        </div>

      </div>
      <OAuthConsentModal
        network="instagram"
        open={consentOpen}
        busy={authorizeMutation.isPending}
        onClose={() => setConsentOpen(false)}
        onContinue={() => authorizeMutation.mutate()}
      />
    </CredPanel>
  )
}
