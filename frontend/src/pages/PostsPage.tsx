import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, useCallback } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import { postsApi, type Post } from "../api/posts"
import { productsApi, type Product } from "../api/products"
import { Plus, Trash2, Loader2, Sparkles } from "lucide-react"

const PERSONAS = [
  { value: "casual", label: "Casual" },
  { value: "profissional", label: "Profissional" },
  { value: "divertido", label: "Divertido" },
  { value: "persuasivo", label: "Persuasivo" },
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
    mutationFn: (data: { text: string; product_ids: number[] }) => postsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["posts"] })
      setModalOpen(false)
    },
    onError: onAuthError,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, text, product_ids }: { id: number; text: string; product_ids: number[] }) =>
      postsApi.update(id, { text, product_ids }),
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

  const handleSave = useCallback(
    (text: string, productIds: number[]) => {
      if (editingPost) {
        updateMutation.mutate({ id: editingPost.id, text, product_ids: productIds })
      } else {
        createMutation.mutate({ text, product_ids: productIds })
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
              Criação de post com copy manual ou gerado por IA.{" "}
              <span className="text-xs">(agendamento/mídia/thread ainda pelo painel Flask)</span>
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
                    <p className="text-gray-900 whitespace-pre-wrap line-clamp-3">{post.text}</p>
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
                    <p className="text-gray-400 text-xs mt-2">
                      {new Date(post.created_at).toLocaleString("pt-BR")}
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setDeleteConfirm(post.id)
                    }}
                    className="p-1.5 rounded hover:bg-red-50 transition-colors text-red-500 shrink-0"
                    title="Remover post"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
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
  onSave: (text: string, productIds: number[]) => void
  loading: boolean
}

function PostModal({ post, onClose, onSave, loading }: PostModalProps) {
  const [text, setText] = useState(post?.text ?? "")
  const [persona, setPersona] = useState("casual")
  const [selectedProductIds, setSelectedProductIds] = useState<number[]>(
    post?.products.map((p) => p.id) ?? [],
  )

  const { data: productsData } = useQuery({
    queryKey: ["products", ""],
    queryFn: () => productsApi.list(),
  })
  const products = productsData?.data ?? []

  const generateMutation = useMutation({
    mutationFn: (productId: number) => postsApi.generateCopy(productId, persona),
    onSuccess: (res) => setText(res.text),
  })

  const toggleProduct = (id: number) => {
    setSelectedProductIds((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id],
    )
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (text.trim()) {
      onSave(text.trim(), selectedProductIds)
    }
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

          <div>
            <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
              Texto do post *
            </label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              required
              rows={6}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
            />
          </div>

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
              disabled={loading || !text.trim()}
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
