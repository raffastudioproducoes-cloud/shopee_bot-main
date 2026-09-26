import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import { credentialsApi, type SimpleNetwork } from "../api/credentials"
import { CheckCircle2, XCircle, Loader2 } from "lucide-react"

const SIMPLE_NETWORKS: { key: SimpleNetwork; label: string }[] = [
  { key: "shopee", label: "Shopee" },
  { key: "x", label: "X (Twitter)" },
  { key: "facebook", label: "Facebook" },
  { key: "kwai", label: "Kwai" },
]

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
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-3xl mx-auto animate-pulse space-y-4">
          <div className="h-8 w-48 bg-gray-200 rounded" />
          <div className="h-64 bg-gray-200 rounded" />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-3xl mx-auto">
        <header className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Credenciais</h1>
          <p className="text-gray-500 mt-1">
            O valor da credencial nunca é reexibido depois de salvo — só o status de conexão.
          </p>
        </header>

        {banner && (
          <div
            className={`mb-4 px-4 py-3 rounded-lg text-sm font-medium ${
              banner.ok
                ? "bg-green-50 text-green-700 border border-green-200"
                : "bg-red-50 text-red-700 border border-red-200"
            }`}
          >
            {banner.text}
          </div>
        )}

        <div className="space-y-4">
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
    </div>
  )
}

// ── Card genérico (Shopee, X, Facebook, Instagram, TikTok, Kwai) ────────────────

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
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-gray-900 font-medium">{label}</h3>
        <StatusBadge connected={connected} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          saveMutation.mutate()
        }}
        className="grid grid-cols-1 sm:grid-cols-2 gap-3"
      >
        <input
          type="text"
          value={appId}
          onChange={(e) => setAppId(e.target.value)}
          placeholder="APP ID"
          required
          className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
        />
        <input
          type="password"
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
          placeholder="Secret"
          autoComplete="off"
          required
          className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
        />
        {isFacebook && (
          <input
            type="text"
            value={pageId}
            onChange={(e) => setPageId(e.target.value)}
            placeholder="Page ID"
            required
            className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none transition sm:col-span-2"
          />
        )}
        <div className="sm:col-span-2 flex justify-end gap-2">
          {connected && (
            <button
              type="button"
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              className="px-3 py-1.5 rounded-lg text-red-600 text-sm hover:bg-red-50 disabled:opacity-50 transition"
            >
              Desconectar
            </button>
          )}
          <button
            type="submit"
            disabled={saveMutation.isPending || !appId || !secret || (isFacebook && !pageId)}
            className="px-4 py-1.5 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-1.5"
          >
            {saveMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Salvar
          </button>
        </div>
      </form>
    </div>
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
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-gray-900 font-medium">Threads</h3>
        <StatusBadge connected={connected} />
      </div>
      <p className="text-xs text-gray-500 mb-4">
        Threads usa OAuth — conecte pela Meta ou, se preferir, cole um token já emitido.
      </p>

      <button
        type="button"
        onClick={() => authorizeMutation.mutate()}
        disabled={authorizeMutation.isPending}
        className="mb-4 px-4 py-1.5 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-1.5"
      >
        {authorizeMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
        Conectar Threads
      </button>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          saveMutation.mutate()
        }}
        className="grid grid-cols-1 sm:grid-cols-2 gap-3"
      >
        <input
          type="text"
          value={tUserId}
          onChange={(e) => setTUserId(e.target.value)}
          placeholder="Threads User ID"
          required
          className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
        />
        <input
          type="password"
          value={accessToken}
          onChange={(e) => setAccessToken(e.target.value)}
          placeholder="Access Token"
          autoComplete="off"
          required
          className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
        />
        <div className="sm:col-span-2 flex justify-end gap-2">
          {connected && (
            <button
              type="button"
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              className="px-3 py-1.5 rounded-lg text-red-600 text-sm hover:bg-red-50 disabled:opacity-50 transition"
            >
              Desconectar
            </button>
          )}
          <button
            type="submit"
            disabled={saveMutation.isPending || !tUserId || !accessToken}
            className="px-4 py-1.5 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-1.5"
          >
            {saveMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Salvar
          </button>
        </div>
      </form>
    </div>
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
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-gray-900 font-medium">TikTok</h3>
        <StatusBadge connected={connected} />
      </div>
      <p className="text-xs text-gray-500 mb-4">
        Salve o Client Key/Secret do seu app TikTok for Developers e depois conecte via OAuth.
      </p>

      <button
        type="button"
        onClick={() => authorizeMutation.mutate()}
        disabled={authorizeMutation.isPending}
        className="mb-4 px-4 py-1.5 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-1.5"
      >
        {authorizeMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
        Conectar TikTok
      </button>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          saveMutation.mutate()
        }}
        className="grid grid-cols-1 sm:grid-cols-2 gap-3"
      >
        <input
          type="text"
          value={appId}
          onChange={(e) => setAppId(e.target.value)}
          placeholder="Client Key"
          required
          className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
        />
        <input
          type="password"
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
          placeholder="Client Secret"
          autoComplete="off"
          required
          className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
        />
        <div className="sm:col-span-2 flex justify-end gap-2">
          {connected && (
            <button
              type="button"
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              className="px-3 py-1.5 rounded-lg text-red-600 text-sm hover:bg-red-50 disabled:opacity-50 transition"
            >
              Desconectar
            </button>
          )}
          <button
            type="submit"
            disabled={saveMutation.isPending || !appId || !secret}
            className="px-4 py-1.5 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-1.5"
          >
            {saveMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Salvar
          </button>
        </div>
      </form>
    </div>
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
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-gray-900 font-medium">Instagram</h3>
        <StatusBadge connected={connected} />
      </div>
      <p className="text-xs text-gray-500 mb-4">
        Publicar exige uma conta Business/Creator vinculada a uma Página do
        Facebook — conecte via Facebook Login for Business, ou salve o App
        ID/Secret do app Meta abaixo.
      </p>

      <button
        type="button"
        onClick={() => authorizeMutation.mutate()}
        disabled={authorizeMutation.isPending}
        className="mb-4 px-4 py-1.5 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-1.5"
      >
        {authorizeMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
        Conectar Instagram
      </button>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          saveMutation.mutate()
        }}
        className="grid grid-cols-1 sm:grid-cols-2 gap-3"
      >
        <input
          type="text"
          value={appId}
          onChange={(e) => setAppId(e.target.value)}
          placeholder="APP ID"
          required
          className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
        />
        <input
          type="password"
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
          placeholder="Secret"
          autoComplete="off"
          required
          className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
        />
        <div className="sm:col-span-2 flex justify-end gap-2">
          {connected && (
            <button
              type="button"
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              className="px-3 py-1.5 rounded-lg text-red-600 text-sm hover:bg-red-50 disabled:opacity-50 transition"
            >
              Desconectar
            </button>
          )}
          <button
            type="submit"
            disabled={saveMutation.isPending || !appId || !secret}
            className="px-4 py-1.5 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-1.5"
          >
            {saveMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Salvar
          </button>
        </div>
      </form>
    </div>
  )
}

function StatusBadge({ connected }: { connected: boolean }) {
  return connected ? (
    <span className="flex items-center gap-1 text-xs font-medium text-green-700 bg-green-50 px-2 py-1 rounded-full">
      <CheckCircle2 className="w-3.5 h-3.5" />
      Conectado
    </span>
  ) : (
    <span className="flex items-center gap-1 text-xs font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
      <XCircle className="w-3.5 h-3.5" />
      Desconectado
    </span>
  )
}
