import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import { credentialsApi, type SimpleNetwork } from "../api/credentials"
import { Panel, PanelHeader } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { TextInput } from "../components/ui/TextInput"
import { StatusBadge } from "../components/ui/StatusBadge"

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

export function CredentialsPage() {
  const { logout } = useAuthStore()
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
    }
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
            connected={status?.[network.key]?.connected ?? false}
            onSaved={invalidate}
            onAuthError={onAuthError}
          />
        ))}

        <ThreadsCredentialCard
          connected={status?.threads?.connected ?? false}
          onSaved={invalidate}
          onAuthError={onAuthError}
        />

        <TikTokCredentialCard
          connected={status?.tiktok?.connected ?? false}
          onSaved={invalidate}
          onAuthError={onAuthError}
        />

        <InstagramCredentialCard
          connected={status?.instagram?.connected ?? false}
          onSaved={invalidate}
          onAuthError={onAuthError}
        />
      </div>
    </div>
  )
}

// ── Card genérico (Shopee, X, Facebook, Kwai) ────────────────────────────────

function SimpleCredentialCard({
  network,
  label,
  connected,
  onSaved,
  onAuthError,
}: {
  network: SimpleNetwork
  label: string
  connected: boolean
  onSaved: () => void
  onAuthError: (err: Error) => void
}) {
  const [appId, setAppId] = useState("")
  const [secret, setSecret] = useState("")
  const [pageId, setPageId] = useState("")
  const isFacebook = network === "facebook"

  const saveMutation = useMutation({
    mutationFn: () => credentialsApi.save(network, appId, secret, isFacebook ? pageId : undefined),
    onSuccess: () => {
      setAppId("")
      setSecret("")
      setPageId("")
      onSaved()
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: () => credentialsApi.delete(network),
    onSuccess: onSaved,
    onError: onAuthError,
  })

  return (
    <Panel surface="dark">
      <PanelHeader
        title={label}
        trailing={
          <StatusBadge tone={connected ? "positive" : "neutral"} icon={connected ? "check-circle-2" : "x-circle"}>
            {connected ? "Conectado" : "Desconectado"}
          </StatusBadge>
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
  connected,
  onSaved,
  onAuthError,
}: {
  connected: boolean
  onSaved: () => void
  onAuthError: (err: Error) => void
}) {
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
      onSaved()
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: () => credentialsApi.deleteThreads(),
    onSuccess: onSaved,
    onError: onAuthError,
  })

  return (
    <Panel surface="dark">
      <PanelHeader
        title="Threads"
        trailing={
          <StatusBadge tone={connected ? "positive" : "neutral"} icon={connected ? "check-circle-2" : "x-circle"}>
            {connected ? "Conectado" : "Desconectado"}
          </StatusBadge>
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
  connected,
  onSaved,
  onAuthError,
}: {
  connected: boolean
  onSaved: () => void
  onAuthError: (err: Error) => void
}) {
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
      onSaved()
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: () => credentialsApi.delete("tiktok"),
    onSuccess: onSaved,
    onError: onAuthError,
  })

  return (
    <Panel surface="dark">
      <PanelHeader
        title="TikTok"
        trailing={
          <StatusBadge tone={connected ? "positive" : "neutral"} icon={connected ? "check-circle-2" : "x-circle"}>
            {connected ? "Conectado" : "Desconectado"}
          </StatusBadge>
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
  connected,
  onSaved,
  onAuthError,
}: {
  connected: boolean
  onSaved: () => void
  onAuthError: (err: Error) => void
}) {
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
      onSaved()
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: () => credentialsApi.delete("instagram"),
    onSuccess: onSaved,
    onError: onAuthError,
  })

  return (
    <Panel surface="dark">
      <PanelHeader
        title="Instagram"
        trailing={
          <StatusBadge tone={connected ? "positive" : "neutral"} icon={connected ? "check-circle-2" : "x-circle"}>
            {connected ? "Conectado" : "Desconectado"}
          </StatusBadge>
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
