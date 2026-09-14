import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import { credentialsApi, type SimpleNetwork } from "../api/credentials"
import { CheckCircle2, XCircle, Loader2 } from "lucide-react"

const SIMPLE_NETWORKS: { key: SimpleNetwork; label: string }[] = [
  { key: "shopee", label: "Shopee" },
  { key: "x", label: "X (Twitter)" },
  { key: "facebook", label: "Facebook" },
  { key: "instagram", label: "Instagram" },
  { key: "tiktok", label: "TikTok" },
  { key: "kwai", label: "Kwai" },
]

export function CredentialsPage() {
  const { logout } = useAuthStore()
  const queryClient = useQueryClient()

  const { data: status, isLoading } = useQuery({
    queryKey: ["credentials"],
    queryFn: () => credentialsApi.list(),
  })

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

  const saveMutation = useMutation({
    mutationFn: () => credentialsApi.save(network, appId, secret),
    onSuccess: () => {
      setAppId("")
      setSecret("")
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
        Threads usa OAuth — gere o token pelo painel Flask (fluxo de callback com a Meta) e cole
        aqui.
      </p>

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
