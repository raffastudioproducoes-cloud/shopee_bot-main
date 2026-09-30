import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import {
  credentialsApi,
  CREDENTIAL_HELP_LINKS,
  type SimpleNetwork,
  type CredentialStatusWithLight,
} from "../api/credentials"
import { Panel, PanelHeader } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { TextInput } from "../components/ui/TextInput"
import { StatusBadge } from "../components/ui/StatusBadge"
import { ConnectionLight } from "../components/ui/ConnectionLight"

// X/Facebook saíram daqui: têm card dedicado (XCredentialCard,
// FacebookCredentialCard — mesmo padrão de TikTok/Instagram) porque usam
// OAuth authorize/callback, não app_id/secret por formulário. Kwai também
// saiu do mapeamento: renderizado à parte, por último, com aviso "em breve"
// pra usuário não-admin (ver comingSoonForNonAdmin em SimpleCredentialCard).
const SIMPLE_NETWORKS: { key: SimpleNetwork; label: string }[] = [
  { key: "shopee", label: "Shopee" },
]

// Grade de 2 colunas que colapsa pra 1 em telas estreitas (mesmo efeito do
// antigo `grid-cols-1 sm:grid-cols-2`, sem depender de breakpoint Tailwind).
const FIELD_GRID = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
  gap: 12,
} as const

const EMPTY_STATUS: CredentialStatusWithLight = {
  connected: false,
  light: "red",
  checked_at: null,
  check_message: null,
}

export function CredentialsPage() {
  const { logout, user } = useAuthStore()
  const isAdmin = user?.access === "ADMIN"
  const queryClient = useQueryClient()
  const [banner, setBanner] = useState<{ ok: boolean; text: string } | null>(null)

  const { data: status, isLoading } = useQuery({
    queryKey: ["credentials"],
    queryFn: () => credentialsApi.list(),
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
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 256, color: "var(--text-muted)" }}>
        Carregando...
      </div>
    )
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap-column)" }}>
      <div>
        <h1 style={{ font: "var(--text-role-hero)", color: "var(--text-display)", margin: 0 }}>Credenciais</h1>
        <p style={{ color: "var(--text-muted)", marginTop: 4 }}>
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

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {SIMPLE_NETWORKS.map((network) => (
          <SimpleCredentialCard
            key={network.key}
            network={network.key}
            label={network.label}
            status={status?.[network.key] ?? EMPTY_STATUS}
            isAdmin={isAdmin}
            onSaved={invalidate}
            onAuthError={onAuthError}
            setBanner={setBanner}
          />
        ))}

        <ThreadsCredentialCard
          status={status?.threads ?? EMPTY_STATUS}
          isAdmin={isAdmin}
          onSaved={invalidate}
          onAuthError={onAuthError}
          setBanner={setBanner}
        />

        <XCredentialCard
          status={status?.x ?? EMPTY_STATUS}
          isAdmin={isAdmin}
          onSaved={invalidate}
          onAuthError={onAuthError}
          setBanner={setBanner}
        />

        <FacebookCredentialCard
          status={status?.facebook ?? EMPTY_STATUS}
          isAdmin={isAdmin}
          onSaved={invalidate}
          onAuthError={onAuthError}
          setBanner={setBanner}
        />

        <InstagramCredentialCard
          status={status?.instagram ?? EMPTY_STATUS}
          isAdmin={isAdmin}
          onSaved={invalidate}
          onAuthError={onAuthError}
          setBanner={setBanner}
        />

        {/* TikTok e Kwai por último, de propósito: ligação com o usuário
            comum ainda não está pronta (TikTok em revisão externa, Kwai sem
            API pública de postagem) — card mostra aviso "em breve" pra
            quem não é admin, ver isAdmin dentro de cada componente. */}
        <TikTokCredentialCard
          status={status?.tiktok ?? EMPTY_STATUS}
          isAdmin={isAdmin}
          onSaved={invalidate}
          onAuthError={onAuthError}
          setBanner={setBanner}
        />

        <SimpleCredentialCard
          network="kwai"
          label="Kwai"
          status={status?.kwai ?? EMPTY_STATUS}
          isAdmin={isAdmin}
          onSaved={invalidate}
          onAuthError={onAuthError}
          setBanner={setBanner}
          comingSoonForNonAdmin
        />
      </div>
    </div>
  )
}

// ── Sinalizador (luz, visível a todo mundo) + botão "Testar conexão"
// (admin-only) compartilhados entre os 7 cards de rede. ─────────────────────

function CredentialTrailing({
  network,
  label,
  status,
  isAdmin,
  onSaved,
  onAuthError,
  setBanner,
}: {
  network: SimpleNetwork | "threads"
  label: string
  status: CredentialStatusWithLight
  isAdmin: boolean
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
    <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", flexWrap: "wrap", gap: 10 }}>
      <ConnectionLight state={status.light} title={status.check_message ?? undefined} />
      <StatusBadge tone={status.connected ? "positive" : "neutral"} icon={status.connected ? "check-circle-2" : "x-circle"}>
        {status.connected ? "Conectado" : "Desconectado"}
      </StatusBadge>
      {isAdmin && (
        <Button
          type="button"
          variant="ghost"
          disabled={testMutation.isPending}
          onClick={() => testMutation.mutate()}
        >
          {testMutation.isPending ? "Testando..." : "Testar conexão"}
        </Button>
      )}
    </div>
  )
}

// ── Link admin-only pro portal de desenvolvedores de cada rede OAuth de app
// único (Threads/X/Facebook/TikTok/Instagram). Quem clica "Conectar" nunca
// precisa disso — é só referência pra quem administra o app da plataforma
// (env vars em api/x_oauth.py, api/tiktok_oauth.py, etc). Não existe pro
// usuário comum: ele só tem o botão OAuth. ────────────────────────────────

function AdminHelpLink({ network, label }: { network: SimpleNetwork | "threads"; label: string }) {
  const helpUrl = CREDENTIAL_HELP_LINKS[network]
  if (!helpUrl) return null
  return (
    <a
      href={helpUrl}
      target="_blank"
      rel="noreferrer"
      style={{ font: "var(--text-role-body)", color: "var(--accent-500)" }}
    >
      Abrir portal de desenvolvedores da {label} (gerenciar app da plataforma) ↗
    </a>
  )
}

// ── Card genérico (Shopee, X, Facebook, Kwai) ────────────────────────────────

function SimpleCredentialCard({
  network,
  label,
  status,
  isAdmin,
  onSaved,
  onAuthError,
  setBanner,
  comingSoonForNonAdmin,
}: {
  network: SimpleNetwork
  label: string
  status: CredentialStatusWithLight
  isAdmin: boolean
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
  comingSoonForNonAdmin?: boolean
}) {
  const [appId, setAppId] = useState("")
  const [secret, setSecret] = useState("")
  const connected = status.connected
  const helpUrl = CREDENTIAL_HELP_LINKS[network]

  const saveMutation = useMutation({
    mutationFn: () => credentialsApi.save(network, appId, secret),
    onSuccess: () => {
      setAppId("")
      setSecret("")
      setBanner({ ok: true, text: `${label} conectado com sucesso.` })
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

  // Kwai (única rede com essa flag hoje): sem API pública de postagem, então
  // usuário comum não vê formulário/status nenhum, só o aviso. Admin
  // continua vendo tudo normal (pode testar App ID/Secret de afiliado).
  if (comingSoonForNonAdmin && !isAdmin) {
    return (
      <Panel surface="dark">
        <PanelHeader title={label} />
        <div style={{ padding: "0 16px 16px" }}>
          <p style={{ margin: 0, color: "var(--text-muted)", font: "var(--text-role-body)" }}>
            Em breve — a ligação com {label} ainda não está disponível.
          </p>
        </div>
      </Panel>
    )
  }

  return (
    <Panel surface="dark">
      <PanelHeader
        title={label}
        trailing={
          <CredentialTrailing
            network={network}
            label={label}
            status={status}
            isAdmin={isAdmin}
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
        style={{ padding: "0 16px 16px", display: "flex", flexDirection: "column", gap: 12 }}
      >
        {helpUrl && (
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <a
              href={helpUrl}
              target="_blank"
              rel="noreferrer"
              style={{ font: "var(--text-role-body)", color: "var(--accent-500)" }}
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
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 18,
                  height: 18,
                  flexShrink: 0,
                  borderRadius: "50%",
                  border: "1px solid currentColor",
                  background: "none",
                  color: "var(--accent-500)",
                  cursor: "pointer",
                  opacity: 0.75,
                  font: "var(--fw-semibold) 10px/1 var(--font-sans)",
                  padding: 0,
                }}
              >
                ?
              </button>
            )}
          </div>
        )}
        <div style={FIELD_GRID}>
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
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
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
    </Panel>
  )
}

// ── Card do Threads (OAuth — cola token já emitido) ─────────────────────────────

function ThreadsCredentialCard({
  status,
  isAdmin,
  onSaved,
  onAuthError,
  setBanner,
}: {
  status: CredentialStatusWithLight
  isAdmin: boolean
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  const connected = status.connected
  const [tUserId, setTUserId] = useState("")
  const [accessToken, setAccessToken] = useState("")

  const authorizeMutation = useMutation({
    mutationFn: () => credentialsApi.authorizeThreads(),
    onSuccess: ({ url }) => {
      window.location.href = url
    },
    onError: onAuthError,
  })

  const saveMutation = useMutation({
    mutationFn: () => credentialsApi.saveThreads(tUserId, accessToken),
    onSuccess: () => {
      setTUserId("")
      setAccessToken("")
      setBanner({ ok: true, text: "Threads conectado com sucesso." })
      onSaved()
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
    <Panel surface="dark">
      <PanelHeader
        title="Threads"
        trailing={
          <CredentialTrailing
            network="threads"
            label="Threads"
            status={status}
            isAdmin={isAdmin}
            onSaved={onSaved}
            onAuthError={onAuthError}
            setBanner={setBanner}
          />
        }
      />

      <div style={{ padding: "0 16px 16px", display: "flex", flexDirection: "column", gap: 12 }}>
        <p style={{ margin: 0, color: "var(--text-muted)", font: "var(--text-role-body)" }}>
          Threads usa OAuth — conecte pela Meta ou, se preferir, cole um token já emitido.
        </p>

        {isAdmin && <AdminHelpLink network="threads" label="Threads" />}

        <div style={{ display: "flex", gap: 8 }}>
          <Button
            type="button"
            variant="primary"
            disabled={authorizeMutation.isPending}
            onClick={() => authorizeMutation.mutate()}
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

        {/* Colar token manualmente é a exceção admin-only aqui: pra usuário
            comum, o fluxo é só o botão OAuth acima (mesma regra das outras
            redes de app único — luz, status e "Conectar", sem caixa de
            token). Admin mantém isso como fallback/debug (ex: token gerado
            fora do fluxo normal). */}
        {isAdmin && (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              saveMutation.mutate()
            }}
            style={{ display: "flex", flexDirection: "column", gap: 12 }}
          >
            <div style={FIELD_GRID}>
              <TextInput
                label="Threads User ID"
                value={tUserId}
                onChange={(e) => setTUserId(e.target.value)}
                placeholder="Threads User ID"
                required
              />
              <TextInput
                label="Access Token"
                type="password"
                value={accessToken}
                onChange={(e) => setAccessToken(e.target.value)}
                placeholder="Access Token"
                autoComplete="off"
                required
              />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <Button
                type="submit"
                variant="primary"
                disabled={saveMutation.isPending || !tUserId || !accessToken}
              >
                {saveMutation.isPending ? "Salvando..." : "Salvar"}
              </Button>
            </div>
          </form>
        )}
      </div>
    </Panel>
  )
}

// ── Card do X (App ID/Secret + OAuth 2.0/PKCE) ──────────────────────────────────

function XCredentialCard({
  status,
  isAdmin,
  onSaved,
  onAuthError,
  setBanner,
}: {
  status: CredentialStatusWithLight
  isAdmin: boolean
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  const connected = status.connected
  const [userAccessToken, setUserAccessToken] = useState("")
  const [userRefreshToken, setUserRefreshToken] = useState("")

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

  const saveManualMutation = useMutation({
    mutationFn: () => credentialsApi.saveXManual(userAccessToken, userRefreshToken || undefined),
    onSuccess: () => {
      setUserAccessToken("")
      setUserRefreshToken("")
      setBanner({ ok: true, text: "X conectado com sucesso (override manual)." })
      onSaved()
    },
    onError: onAuthError,
  })

  return (
    <Panel surface="dark">
      <PanelHeader
        title="X (Twitter)"
        trailing={
          <CredentialTrailing
            network="x"
            label="X"
            status={status}
            isAdmin={isAdmin}
            onSaved={onSaved}
            onAuthError={onAuthError}
            setBanner={setBanner}
          />
        }
      />

      <div style={{ padding: "0 16px 16px", display: "flex", flexDirection: "column", gap: 12 }}>
        <p style={{ margin: 0, color: "var(--text-muted)", font: "var(--text-role-body)" }}>
          Conecte sua conta do X com um clique — nenhuma configuração técnica necessária.
        </p>

        {isAdmin && <AdminHelpLink network="x" label="X" />}

        <div style={{ display: "flex", gap: 8 }}>
          <Button
            type="button"
            variant="primary"
            disabled={authorizeMutation.isPending}
            onClick={() => authorizeMutation.mutate()}
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

        {/* Override manual admin-only — colar token direto, sem passar pelo
            OAuth (debug/emergência, ex: testar com uma conta específica).
            Mesma exceção admin-only do Threads acima. */}
        {isAdmin && (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              saveManualMutation.mutate()
            }}
            style={{ display: "flex", flexDirection: "column", gap: 12 }}
          >
            <div style={FIELD_GRID}>
              <TextInput
                label="Access Token"
                type="password"
                value={userAccessToken}
                onChange={(e) => setUserAccessToken(e.target.value)}
                placeholder="Access Token"
                autoComplete="off"
                required
              />
              <TextInput
                label="Refresh Token (opcional)"
                type="password"
                value={userRefreshToken}
                onChange={(e) => setUserRefreshToken(e.target.value)}
                placeholder="Refresh Token"
                autoComplete="off"
              />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <Button
                type="submit"
                variant="primary"
                disabled={saveManualMutation.isPending || !userAccessToken}
              >
                {saveManualMutation.isPending ? "Salvando..." : "Salvar (override manual)"}
              </Button>
            </div>
          </form>
        )}
      </div>
    </Panel>
  )
}

// ── Card do Facebook (OAuth de app único — clicar "Conectar Facebook") ──────────

function FacebookCredentialCard({
  status,
  isAdmin,
  onSaved,
  onAuthError,
  setBanner,
}: {
  status: CredentialStatusWithLight
  isAdmin: boolean
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  const connected = status.connected
  const [pageId, setPageId] = useState("")
  const [pageAccessToken, setPageAccessToken] = useState("")
  const [pageName, setPageName] = useState("")

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

  const saveManualMutation = useMutation({
    mutationFn: () => credentialsApi.saveFacebookManual(pageId, pageAccessToken, pageName || undefined),
    onSuccess: () => {
      setPageId("")
      setPageAccessToken("")
      setPageName("")
      setBanner({ ok: true, text: "Facebook conectado com sucesso (override manual)." })
      onSaved()
    },
    onError: onAuthError,
  })

  return (
    <Panel surface="dark">
      <PanelHeader
        title="Facebook"
        trailing={
          <CredentialTrailing
            network="facebook"
            label="Facebook"
            status={status}
            isAdmin={isAdmin}
            onSaved={onSaved}
            onAuthError={onAuthError}
            setBanner={setBanner}
          />
        }
      />

      <div style={{ padding: "0 16px 16px", display: "flex", flexDirection: "column", gap: 12 }}>
        <p style={{ margin: 0, color: "var(--text-muted)", font: "var(--text-role-body)" }}>
          Conecte a Página do Facebook com um clique — nenhuma configuração técnica necessária.
          Se você administra mais de uma Página, a primeira encontrada é conectada automaticamente.
        </p>

        {isAdmin && <AdminHelpLink network="facebook" label="Facebook" />}

        <div style={{ display: "flex", gap: 8 }}>
          <Button
            type="button"
            variant="primary"
            disabled={authorizeMutation.isPending}
            onClick={() => authorizeMutation.mutate()}
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

        {/* Override manual admin-only — colar page_id/page_access_token
            direto, sem passar pelo OAuth (debug/emergência). Mesma exceção
            admin-only do Threads acima. */}
        {isAdmin && (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              saveManualMutation.mutate()
            }}
            style={{ display: "flex", flexDirection: "column", gap: 12 }}
          >
            <div style={FIELD_GRID}>
              <TextInput
                label="Page ID"
                value={pageId}
                onChange={(e) => setPageId(e.target.value)}
                placeholder="Page ID"
                required
              />
              <TextInput
                label="Page Access Token"
                type="password"
                value={pageAccessToken}
                onChange={(e) => setPageAccessToken(e.target.value)}
                placeholder="Page Access Token"
                autoComplete="off"
                required
              />
              <TextInput
                label="Page Name (opcional)"
                value={pageName}
                onChange={(e) => setPageName(e.target.value)}
                placeholder="Page Name"
              />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <Button
                type="submit"
                variant="primary"
                disabled={saveManualMutation.isPending || !pageId || !pageAccessToken}
              >
                {saveManualMutation.isPending ? "Salvando..." : "Salvar (override manual)"}
              </Button>
            </div>
          </form>
        )}
      </div>
    </Panel>
  )
}

// ── Card do TikTok (OAuth de app único — clicar "Conectar TikTok") ──────────────

function TikTokCredentialCard({
  status,
  isAdmin,
  onSaved,
  onAuthError,
  setBanner,
}: {
  status: CredentialStatusWithLight
  isAdmin: boolean
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  const connected = status.connected
  const [openId, setOpenId] = useState("")
  const [userAccessToken, setUserAccessToken] = useState("")
  const [refreshToken, setRefreshToken] = useState("")

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

  const saveManualMutation = useMutation({
    mutationFn: () => credentialsApi.saveTiktokManual(openId, userAccessToken, refreshToken || undefined),
    onSuccess: () => {
      setOpenId("")
      setUserAccessToken("")
      setRefreshToken("")
      setBanner({ ok: true, text: "TikTok conectado com sucesso (override manual)." })
      onSaved()
    },
    onError: onAuthError,
  })

  // App em revisão na TikTok for Developers (bloqueio externo) — usuário
  // comum não vê botão "Conectar" nem status, só o aviso. Admin continua
  // vendo tudo pra acompanhar/testar assim que a revisão aprovar.
  if (!isAdmin) {
    return (
      <Panel surface="dark">
        <PanelHeader title="TikTok" />
        <div style={{ padding: "0 16px 16px" }}>
          <p style={{ margin: 0, color: "var(--text-muted)", font: "var(--text-role-body)" }}>
            Em breve — a ligação com TikTok ainda não está disponível.
          </p>
        </div>
      </Panel>
    )
  }

  return (
    <Panel surface="dark">
      <PanelHeader
        title="TikTok"
        trailing={
          <CredentialTrailing
            network="tiktok"
            label="TikTok"
            status={status}
            isAdmin={isAdmin}
            onSaved={onSaved}
            onAuthError={onAuthError}
            setBanner={setBanner}
          />
        }
      />

      <div style={{ padding: "0 16px 16px", display: "flex", flexDirection: "column", gap: 12 }}>
        <p style={{ margin: 0, color: "var(--text-muted)", font: "var(--text-role-body)" }}>
          Conecte sua conta do TikTok com um clique — nenhuma configuração técnica necessária.
        </p>

        {isAdmin && <AdminHelpLink network="tiktok" label="TikTok" />}

        <div style={{ display: "flex", gap: 8 }}>
          <Button
            type="button"
            variant="primary"
            disabled={authorizeMutation.isPending}
            onClick={() => authorizeMutation.mutate()}
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

        {/* Override manual admin-only — colar open_id/access_token direto,
            sem passar pelo OAuth (debug/emergência). Mesma exceção
            admin-only do Threads acima. */}
        {isAdmin && (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              saveManualMutation.mutate()
            }}
            style={{ display: "flex", flexDirection: "column", gap: 12 }}
          >
            <div style={FIELD_GRID}>
              <TextInput
                label="Open ID"
                value={openId}
                onChange={(e) => setOpenId(e.target.value)}
                placeholder="Open ID"
                required
              />
              <TextInput
                label="Access Token"
                type="password"
                value={userAccessToken}
                onChange={(e) => setUserAccessToken(e.target.value)}
                placeholder="Access Token"
                autoComplete="off"
                required
              />
              <TextInput
                label="Refresh Token (opcional)"
                type="password"
                value={refreshToken}
                onChange={(e) => setRefreshToken(e.target.value)}
                placeholder="Refresh Token"
                autoComplete="off"
              />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <Button
                type="submit"
                variant="primary"
                disabled={saveManualMutation.isPending || !openId || !userAccessToken}
              >
                {saveManualMutation.isPending ? "Salvando..." : "Salvar (override manual)"}
              </Button>
            </div>
          </form>
        )}
      </div>
    </Panel>
  )
}

// ── Card do Instagram (OAuth de app único via Facebook Login for Business) ─────

function InstagramCredentialCard({
  status,
  isAdmin,
  onSaved,
  onAuthError,
  setBanner,
}: {
  status: CredentialStatusWithLight
  isAdmin: boolean
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  const connected = status.connected
  const [igUserId, setIgUserId] = useState("")
  const [userAccessToken, setUserAccessToken] = useState("")

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

  const saveManualMutation = useMutation({
    mutationFn: () => credentialsApi.saveInstagramManual(igUserId, userAccessToken),
    onSuccess: () => {
      setIgUserId("")
      setUserAccessToken("")
      setBanner({ ok: true, text: "Instagram conectado com sucesso (override manual)." })
      onSaved()
    },
    onError: onAuthError,
  })

  return (
    <Panel surface="dark">
      <PanelHeader
        title="Instagram"
        trailing={
          <CredentialTrailing
            network="instagram"
            label="Instagram"
            status={status}
            isAdmin={isAdmin}
            onSaved={onSaved}
            onAuthError={onAuthError}
            setBanner={setBanner}
          />
        }
      />

      <div style={{ padding: "0 16px 16px", display: "flex", flexDirection: "column", gap: 12 }}>
        <p style={{ margin: 0, color: "var(--text-muted)", font: "var(--text-role-body)" }}>
          Publicar exige uma conta Business/Creator vinculada a uma Página do Facebook — conecte
          com um clique, nenhuma configuração técnica necessária.
        </p>

        {isAdmin && <AdminHelpLink network="instagram" label="Instagram" />}

        <div style={{ display: "flex", gap: 8 }}>
          <Button
            type="button"
            variant="primary"
            disabled={authorizeMutation.isPending}
            onClick={() => authorizeMutation.mutate()}
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

        {/* Override manual admin-only — colar ig_user_id/access_token
            direto, sem passar pelo OAuth (debug/emergência). Mesma
            exceção admin-only do Threads acima. */}
        {isAdmin && (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              saveManualMutation.mutate()
            }}
            style={{ display: "flex", flexDirection: "column", gap: 12 }}
          >
            <div style={FIELD_GRID}>
              <TextInput
                label="Instagram User ID"
                value={igUserId}
                onChange={(e) => setIgUserId(e.target.value)}
                placeholder="IG User ID"
                required
              />
              <TextInput
                label="Access Token"
                type="password"
                value={userAccessToken}
                onChange={(e) => setUserAccessToken(e.target.value)}
                placeholder="Access Token"
                autoComplete="off"
                required
              />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <Button
                type="submit"
                variant="primary"
                disabled={saveManualMutation.isPending || !igUserId || !userAccessToken}
              >
                {saveManualMutation.isPending ? "Salvando..." : "Salvar (override manual)"}
              </Button>
            </div>
          </form>
        )}
      </div>
    </Panel>
  )
}
