import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import {
  credentialsApi,
  type SimpleNetwork,
  type CredentialStatusWithLight,
} from "../api/credentials"
import { Panel, PanelHeader } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { TextInput } from "../components/ui/TextInput"
import { StatusBadge } from "../components/ui/StatusBadge"
import { ConnectionLight } from "../components/ui/ConnectionLight"

const SIMPLE_NETWORKS: { key: SimpleNetwork; label: string }[] = [
  { key: "shopee", label: "Shopee" },
  { key: "x", label: "X (Twitter)" },
  { key: "facebook", label: "Facebook" },
  { key: "kwai", label: "Kwai" },
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

        <TikTokCredentialCard
          status={status?.tiktok ?? EMPTY_STATUS}
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

// ── Card genérico (Shopee, X, Facebook, Kwai) ────────────────────────────────

function SimpleCredentialCard({
  network,
  label,
  status,
  isAdmin,
  onSaved,
  onAuthError,
  setBanner,
}: {
  network: SimpleNetwork
  label: string
  status: CredentialStatusWithLight
  isAdmin: boolean
  onSaved: () => void
  onAuthError: (err: Error) => void
  setBanner: (b: { ok: boolean; text: string } | null) => void
}) {
  const [appId, setAppId] = useState("")
  const [secret, setSecret] = useState("")
  const [pageId, setPageId] = useState("")
  const isFacebook = network === "facebook"
  const connected = status.connected

  const saveMutation = useMutation({
    mutationFn: () => credentialsApi.save(network, appId, secret, isFacebook ? pageId : undefined),
    onSuccess: () => {
      setAppId("")
      setSecret("")
      setPageId("")
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
        {isFacebook && (
          <TextInput
            label="Page ID"
            value={pageId}
            onChange={(e) => setPageId(e.target.value)}
            placeholder="Page ID"
            required
          />
        )}
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
            disabled={saveMutation.isPending || !appId || !secret || (isFacebook && !pageId)}
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

        <Button
          type="button"
          variant="primary"
          disabled={authorizeMutation.isPending}
          onClick={() => authorizeMutation.mutate()}
          style={{ alignSelf: "flex-start" }}
        >
          {authorizeMutation.isPending ? "Conectando..." : "Conectar Threads"}
        </Button>

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
              disabled={saveMutation.isPending || !tUserId || !accessToken}
            >
              {saveMutation.isPending ? "Salvando..." : "Salvar"}
            </Button>
          </div>
        </form>
      </div>
    </Panel>
  )
}

// ── Card do TikTok (Client Key/Secret + OAuth) ──────────────────────────────────

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
  const [appId, setAppId] = useState("")
  const [secret, setSecret] = useState("")

  const authorizeMutation = useMutation({
    mutationFn: () => credentialsApi.authorizeTiktok(),
    onSuccess: ({ url }) => {
      window.location.href = url
    },
    onError: onAuthError,
  })

  const saveMutation = useMutation({
    mutationFn: () => credentialsApi.save("tiktok", appId, secret),
    onSuccess: () => {
      setAppId("")
      setSecret("")
      setBanner({ ok: true, text: "Client Key/Secret do TikTok salvos." })
      onSaved()
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
          Salve o Client Key/Secret do seu app TikTok for Developers e depois conecte via OAuth.
        </p>

        <Button
          type="button"
          variant="primary"
          disabled={authorizeMutation.isPending}
          onClick={() => authorizeMutation.mutate()}
          style={{ alignSelf: "flex-start" }}
        >
          {authorizeMutation.isPending ? "Conectando..." : "Conectar TikTok"}
        </Button>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            saveMutation.mutate()
          }}
          style={{ display: "flex", flexDirection: "column", gap: 12 }}
        >
          <div style={FIELD_GRID}>
            <TextInput
              label="Client Key"
              value={appId}
              onChange={(e) => setAppId(e.target.value)}
              placeholder="Client Key"
              required
            />
            <TextInput
              label="Client Secret"
              type="password"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              placeholder="Client Secret"
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
            <Button type="submit" variant="primary" disabled={saveMutation.isPending || !appId || !secret}>
              {saveMutation.isPending ? "Salvando..." : "Salvar"}
            </Button>
          </div>
        </form>
      </div>
    </Panel>
  )
}

// ── Card do Instagram (App ID/Secret + Facebook Login for Business) ────────────

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
  const [appId, setAppId] = useState("")
  const [secret, setSecret] = useState("")

  const authorizeMutation = useMutation({
    mutationFn: () => credentialsApi.authorizeInstagram(),
    onSuccess: ({ url }) => {
      window.location.href = url
    },
    onError: onAuthError,
  })

  const saveMutation = useMutation({
    mutationFn: () => credentialsApi.save("instagram", appId, secret),
    onSuccess: () => {
      setAppId("")
      setSecret("")
      setBanner({ ok: true, text: "App ID/Secret do Instagram salvos." })
      onSaved()
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
          via Facebook Login for Business, ou salve o App ID/Secret do app Meta abaixo.
        </p>

        <Button
          type="button"
          variant="primary"
          disabled={authorizeMutation.isPending}
          onClick={() => authorizeMutation.mutate()}
          style={{ alignSelf: "flex-start" }}
        >
          {authorizeMutation.isPending ? "Conectando..." : "Conectar Instagram"}
        </Button>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            saveMutation.mutate()
          }}
          style={{ display: "flex", flexDirection: "column", gap: 12 }}
        >
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
            <Button type="submit" variant="primary" disabled={saveMutation.isPending || !appId || !secret}>
              {saveMutation.isPending ? "Salvando..." : "Salvar"}
            </Button>
          </div>
        </form>
      </div>
    </Panel>
  )
}
