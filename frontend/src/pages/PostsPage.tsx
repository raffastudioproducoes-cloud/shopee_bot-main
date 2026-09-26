import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, useCallback } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import { postsApi, type Post, type PostSchedule, type PostNetwork } from "../api/posts"
import { productsApi, type Product } from "../api/products"
import { Plus, Trash2, Loader2, Sparkles, Send, Clock } from "lucide-react"

const PERSONAS = [
  { value: "casual", label: "Casual" },
  { value: "profissional", label: "Profissional" },
  { value: "divertido", label: "Divertido" },
  { value: "persuasivo", label: "Persuasivo" },
]

// Mesmo mapa network -> func do backend (api/routers/posts.py). Só
// Threads publica de verdade hoje — as outras 4 já roteiam pro
// scheduler certo, mas o wrapper de publicação ainda não existe
// (ver NETWORK_FUNC_MAP). Kwai fica de fora, sem API pública ainda.
const NETWORKS: { value: PostNetwork; label: string }[] = [
  { value: "threads", label: "Threads" },
  { value: "x", label: "X (Twitter)" },
  { value: "facebook", label: "Facebook" },
  { value: "instagram", label: "Instagram" },
  { value: "tiktok", label: "TikTok" },
]

const WEEKDAYS = [
  { value: 0, label: "Domingo" },
  { value: 1, label: "Segunda" },
  { value: 2, label: "Terça" },
  { value: 3, label: "Quarta" },
  { value: 4, label: "Quinta" },
  { value: 5, label: "Sexta" },
  { value: 6, label: "Sábado" },
]

export function PostsPage() {
  const { logout } = useAuthStore()
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingPost, setEditingPost] = useState<Post | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)

  const { data: postsData, isLoading } = useQuery({
    queryKey: ["posts"],
    queryFn: () => postsApi.list(),
  })

  const posts = postsData?.data ?? []

  const onAuthError = useCallback(
    (err: Error) => {
      if (err.message.includes("401") || err.message === "Não autenticado") {
        logout()
        router.navigate({ to: "/login" })
      }
    },
    [logout],
  )

  const createMutation = useMutation({
    mutationFn: async (data: {
      texts: string[]
      product_ids: number[]
      schedule: PostSchedule
      network: PostNetwork
      files: File[]
    }) => {
      const created = await postsApi.create({
        texts: data.texts,
        product_ids: data.product_ids,
        schedule: data.schedule,
        network: data.network,
      })
      for (const file of data.files) {
        await postsApi.uploadMedia(created.id, file)
      }
      return created
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["posts"] })
      setModalOpen(false)
    },
    onError: onAuthError,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, texts, product_ids }: { id: number; texts: string[]; product_ids: number[] }) =>
      postsApi.update(id, { texts, product_ids }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["posts"] })
      setModalOpen(false)
      setEditingPost(null)
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => postsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["posts"] })
      setDeleteConfirm(null)
    },
    onError: onAuthError,
  })

  const publishMutation = useMutation({
    mutationFn: (id: number) => postsApi.publishNow(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["posts"] }),
    onError: onAuthError,
  })

  const handleSave = useCallback(
    (
      texts: string[],
      productIds: number[],
      schedule: PostSchedule,
      network: PostNetwork,
      files: File[],
    ) => {
      if (editingPost) {
        updateMutation.mutate({ id: editingPost.id, texts, product_ids: productIds })
      } else {
        createMutation.mutate({ texts, product_ids: productIds, schedule, network, files })
      }
    },
    [editingPost, createMutation, updateMutation],
  )

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto animate-pulse space-y-4">
          <div className="h-8 w-40 bg-gray-200 rounded" />
          <div className="h-96 bg-gray-200 rounded" />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <header className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Posts</h1>
            <p className="text-gray-500 mt-1">
              Criação de post (com thread multi-parte) com copy manual ou gerado por IA, agendado
              ou publicado na hora.{" "}
              <span className="text-xs">(mídia/anexo ainda pelo painel Flask)</span>
            </p>
          </div>
          <button
            onClick={() => {
              setEditingPost(null)
              setModalOpen(true)
            }}
            className="px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover transition flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Novo post
          </button>
        </header>

        {posts.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <p className="text-gray-500 text-sm">Nenhum post criado.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {posts.map((post) => (
              <div
                key={post.id}
                className="bg-white rounded-xl border border-gray-200 p-4 hover:border-gray-300 transition-colors cursor-pointer"
                onClick={() => {
                  setEditingPost(post)
                  setModalOpen(true)
                }}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-gray-900 whitespace-pre-wrap line-clamp-3 flex-1">{post.text}</p>
                    </div>
                    {post.products.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {post.products.map((p) => (
                          <span
                            key={p.id}
                            className="text-xs bg-primary-light text-primary px-2 py-0.5 rounded-full"
                          >
                            {p.name}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="flex items-center gap-3 mt-2">
                      <p className="text-gray-400 text-xs">
                        {new Date(post.created_at).toLocaleString("pt-BR")}
                      </p>
                      {post.scheduled && (
                        <span className="flex items-center gap-1 text-xs text-primary">
                          <Clock className="w-3 h-3" />
                          Agendado
                        </span>
                      )}
                      {!!post.parts_count && post.parts_count > 1 && (
                        <span className="text-xs text-gray-400">{post.parts_count} partes</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {post.scheduled && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          publishMutation.mutate(post.id)
                        }}
                        disabled={publishMutation.isPending}
                        className="p-1.5 rounded hover:bg-primary-light transition-colors text-primary disabled:opacity-50"
                        title="Publicar agora"
                      >
                        {publishMutation.isPending && publishMutation.variables === post.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Send className="w-4 h-4" />
                        )}
                      </button>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setDeleteConfirm(post.id)
                      }}
                      className="p-1.5 rounded hover:bg-red-50 transition-colors text-red-500"
                      title="Remover post"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                {publishMutation.isError && publishMutation.variables === post.id && (
                  <p className="text-xs text-red-600 mt-2">{publishMutation.error.message}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {modalOpen && (
        <PostModal
          post={editingPost}
          onClose={() => {
            setModalOpen(false)
            setEditingPost(null)
          }}
          onSave={handleSave}
          loading={createMutation.isPending || updateMutation.isPending}
          error={createMutation.error?.message}
        />
      )}

      {deleteConfirm != null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-sm w-full p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-2">Confirmar remoção</h2>
            <p className="text-gray-500 text-sm mb-6">
              Tem certeza que deseja remover este post? Esta ação não pode ser desfeita.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 rounded-lg text-gray-600 hover:bg-gray-100 transition"
              >
                Cancelar
              </button>
              <button
                onClick={() => deleteMutation.mutate(deleteConfirm)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 rounded-lg bg-red-500 text-white text-sm font-medium hover:bg-red-600 disabled:opacity-50 transition"
              >
                {deleteMutation.isPending ? "Removendo..." : "Remover"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Modal de criação/edição ─────────────────────────────────────────────────────

interface PostModalProps {
  post: Post | null
  onClose: () => void
  onSave: (
    texts: string[],
    productIds: number[],
    schedule: PostSchedule,
    network: PostNetwork,
    files: File[],
  ) => void
  loading: boolean
  error?: string
}

type WhenOption = "now" | "date" | "cron"

function PostModal({ post, onClose, onSave, loading, error }: PostModalProps) {
  const queryClient = useQueryClient()
  const [texts, setTexts] = useState<string[]>(
    post?.texts && post.texts.length > 0 ? post.texts : [""],
  )
  const [persona, setPersona] = useState("casual")
  const [network, setNetwork] = useState<PostNetwork>(post?.network ?? "threads")
  const [selectedProductIds, setSelectedProductIds] = useState<number[]>(
    post?.products.map((p) => p.id) ?? [],
  )
  const [when, setWhen] = useState<WhenOption>("now")
  const [runDate, setRunDate] = useState("")
  const [cronTime, setCronTime] = useState("09:00")
  const [cronDay, setCronDay] = useState(1)
  const [pendingFiles, setPendingFiles] = useState<File[]>([])

  const { data: productsData } = useQuery({
    queryKey: ["products", ""],
    queryFn: () => productsApi.list(),
  })
  const products = productsData?.data ?? []

  const generateMutation = useMutation({
    mutationFn: (productId: number) => postsApi.generateCopy(productId, persona),
    onSuccess: (res) => setTexts((prev) => [res.text, ...prev.slice(1)]),
  })

  // upload/remoção de mídia num post já existente (edição) rodam na
  // hora — o post_id já existe. Num post novo, os arquivos ficam em
  // pendingFiles e sobem só depois que o post é criado (ver PostsPage).
  const addMediaMutation = useMutation({
    mutationFn: (file: File) => postsApi.uploadMedia(post!.id, file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["posts"] }),
  })

  const deleteMediaMutation = useMutation({
    mutationFn: (mediaId: number) => postsApi.deleteMedia(post!.id, mediaId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["posts"] }),
  })

  const toggleProduct = (id: number) => {
    setSelectedProductIds((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id],
    )
  }

  const setPartText = (index: number, value: string) => {
    setTexts((prev) => prev.map((t, i) => (i === index ? value : t)))
  }

  const addPart = () => setTexts((prev) => [...prev, ""])
  const removePart = (index: number) => setTexts((prev) => prev.filter((_, i) => i !== index))

  const buildSchedule = (): PostSchedule => {
    if (when === "cron") {
      return { trigger: "cron", time: cronTime, day_of_week: cronDay }
    }
    const runAt = when === "now" ? new Date().toISOString() : new Date(runDate).toISOString()
    return { trigger: "date", run_date: runAt }
  }

  const trimmedTexts = texts.map((t) => t.trim()).filter(Boolean)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (trimmedTexts.length === 0) return
    if (when === "date" && !runDate) return
    onSave(trimmedTexts, selectedProductIds, buildSchedule(), network, pendingFiles)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">{post ? "Editar post" : "Novo post"}</h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
              Produtos
            </label>
            <div className="max-h-32 overflow-y-auto border border-gray-200 rounded-lg p-2 space-y-1">
              {products.length === 0 && (
                <p className="text-xs text-gray-400 px-1">Nenhum produto cadastrado ainda.</p>
              )}
              {products.map((product: Product) => (
                <label key={product.id} className="flex items-center gap-2 text-sm px-1 py-0.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedProductIds.includes(product.id)}
                    onChange={() => toggleProduct(product.id)}
                    className="rounded border-gray-300"
                  />
                  {product.name}
                </label>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={persona}
              onChange={(e) => setPersona(e.target.value)}
              className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none"
            >
              {PERSONAS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={selectedProductIds.length === 0 || generateMutation.isPending}
              onClick={() => generateMutation.mutate(selectedProductIds[0])}
              className="px-3 py-2 rounded-lg bg-primary-light text-primary text-sm font-medium hover:brightness-95 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-1.5"
              title={selectedProductIds.length === 0 ? "Selecione um produto primeiro" : "Gerar texto com IA"}
            >
              {generateMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              Gerar texto com IA
            </button>
          </div>
          {generateMutation.isError && (
            <p className="text-xs text-red-600">{generateMutation.error.message}</p>
          )}

          <div className="space-y-3">
            {texts.map((partText, index) => (
              <div key={index}>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {index === 0 ? "Texto do post *" : `Parte ${index + 1} (resposta em thread)`}
                  </label>
                  {texts.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removePart(index)}
                      className="text-xs text-red-500 hover:text-red-700"
                    >
                      Remover parte
                    </button>
                  )}
                </div>
                <textarea
                  value={partText}
                  onChange={(e) => setPartText(index, e.target.value)}
                  required={index === 0}
                  rows={index === 0 ? 6 : 3}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
                />
              </div>
            ))}
            <button
              type="button"
              onClick={addPart}
              className="text-sm text-primary hover:text-primary-hover font-medium flex items-center gap-1"
            >
              <Plus className="w-3.5 h-3.5" />
              Adicionar parte (thread)
            </button>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
              Mídia (imagem/vídeo)
            </label>
            {post && post.medias.length > 0 && (
              <ul className="space-y-1 mb-2">
                {post.medias.map((media) => (
                  <li
                    key={media.id}
                    className="flex items-center justify-between text-sm bg-gray-50 rounded-lg px-3 py-1.5"
                  >
                    <span className="truncate">{media.file_name}</span>
                    <button
                      type="button"
                      onClick={() => deleteMediaMutation.mutate(media.id)}
                      disabled={deleteMediaMutation.isPending}
                      className="text-red-500 hover:text-red-700 text-xs shrink-0 ml-2"
                    >
                      Remover
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <input
              type="file"
              accept=".webp,.jpg,.jpeg,.png,.gif,.mp4"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (!file) return
                if (post) {
                  addMediaMutation.mutate(file)
                } else {
                  setPendingFiles((prev) => [...prev, file])
                }
                e.target.value = ""
              }}
              className="text-sm"
            />
            {!post && pendingFiles.length > 0 && (
              <ul className="space-y-1 mt-2">
                {pendingFiles.map((file, index) => (
                  <li
                    key={index}
                    className="flex items-center justify-between text-sm bg-gray-50 rounded-lg px-3 py-1.5"
                  >
                    <span className="truncate">{file.name}</span>
                    <button
                      type="button"
                      onClick={() => setPendingFiles((prev) => prev.filter((_, i) => i !== index))}
                      className="text-red-500 hover:text-red-700 text-xs shrink-0 ml-2"
                    >
                      Remover
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {addMediaMutation.isError && (
              <p className="text-xs text-red-600 mt-1">{addMediaMutation.error.message}</p>
            )}
          </div>

          {!post && (
            <div>
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
                Rede social
              </label>
              <select
                value={network}
                onChange={(e) => setNetwork(e.target.value as PostNetwork)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none"
              >
                {NETWORKS.map((n) => (
                  <option key={n.value} value={n.value}>
                    {n.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {!post && (
            <div>
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                Quando publicar? *
              </label>
              <div className="flex gap-2 mb-3">
                {(
                  [
                    ["now", "Agora"],
                    ["date", "Data específica"],
                    ["cron", "Recorrente"],
                  ] as [WhenOption, string][]
                ).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setWhen(value)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                      when === value
                        ? "bg-primary text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {when === "date" && (
                <input
                  type="datetime-local"
                  value={runDate}
                  onChange={(e) => setRunDate(e.target.value)}
                  required
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
                />
              )}

              {when === "cron" && (
                <div className="grid grid-cols-2 gap-3">
                  <select
                    value={cronDay}
                    onChange={(e) => setCronDay(Number(e.target.value))}
                    className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none"
                  >
                    {WEEKDAYS.map((d) => (
                      <option key={d.value} value={d.value}>
                        {d.label}
                      </option>
                    ))}
                  </select>
                  <input
                    type="time"
                    value={cronTime}
                    onChange={(e) => setCronTime(e.target.value)}
                    className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none"
                  />
                </div>
              )}
            </div>
          )}

          {error && <p className="text-xs text-red-600">{error}</p>}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-gray-600 hover:bg-gray-100 transition"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading || trimmedTexts.length === 0 || (when === "date" && !runDate)}
              className="px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {loading ? "Salvando..." : post ? "Salvar" : "Criar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
