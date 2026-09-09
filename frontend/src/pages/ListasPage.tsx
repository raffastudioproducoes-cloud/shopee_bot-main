import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, useCallback } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"

// ── Listas de Produtos Page ──────────────────────────────────────────────────────

interface ProductListItem {
  id: number
  name: string
  image: string | null
  price_min: number | null
  price_max: number | null
  commission: number | null
  commission_link: string | null
  original_link: string | null
}

interface ProductList {
  id: number
  name: string
  created_at: string
  updated_at: string | null
  products: ProductListItem[] | null
  product_count?: number
}

interface ListsResponse {
  data: ProductList[]
  next_cursor: string | null
}

export function ListasPage() {
  const { accessToken, logout } = useAuthStore()
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingList, setEditingList] = useState<ProductList | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)

  const { data: listsData, isLoading, error } = useQuery<ListsResponse>({
    queryKey: ["lists"],
    queryFn: async () => {
      const res = await fetch("/api/lists/", {
        credentials: "include",
      })
      if (!res.ok) {
        if (res.status === 401) {
          logout()
          throw new Error("Não autenticado")
        }
        throw new Error("Falha ao buscar listas")
      }
      return res.json()
    },
  })

  const lists = listsData?.data ?? []

  // ── Create mutation ─────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: async (name: string) => {
      const res = await fetch("/api/lists/", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Falha ao criar lista" }))
        throw new Error(err.detail || "Falha ao criar lista")
      }
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lists"] })
      setModalOpen(false)
    },
    onError: (err: Error) => {
      if (err.message === "Não autenticado") {
        logout()
        router.navigate({ to: "/login" })
      }
    },
  })

  // ── Delete mutation ─────────────────────────────────────────────────────────────

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await fetch(`/api/lists/${id}`, {
        method: "DELETE",
        credentials: "include",
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Falha ao remover lista" }))
        throw new Error(err.detail || "Falha ao remover lista")
      }
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lists"] })
      setDeleteConfirm(null)
    },
    onError: (err: Error) => {
      if (err.message === "Não autenticado") {
        logout()
        router.navigate({ to: "/login" })
      }
    },
  })

  // ── Handlers ────────────────────────────────────────────────────────────────────

  const handleCreate = useCallback(
    (name: string) => {
      createMutation.mutate(name)
    },
    [createMutation],
  )

  const handleDelete = useCallback(
    (id: number) => {
      deleteMutation.mutate(id)
    },
    [deleteMutation],
  )

  // ── Loading ─────────────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="min-h-screen bg-surface p-6">
        <div className="max-w-4xl mx-auto">
          <div className="animate-pulse space-y-4">
            <div className="h-8 w-40 bg-surface-container rounded" />
            <div className="h-96 bg-surface-container rounded" />
          </div>
        </div>
      </div>
    )
  }

  // ── Error / not authenticated ───────────────────────────────────────────────────

  if (!listsData) {
    return (
      <div className="min-h-screen bg-surface p-6">
        <div className="max-w-4xl mx-auto text-center py-12">
          <p className="text-on-surface-variant">Erro ao carregar as listas.</p>
          <button
            onClick={() => router.navigate({ to: "/login" })}
            className="mt-4 px-4 py-2 rounded bg-accent text-on-accent"
          >
            Voltar ao login
          </button>
        </div>
      </div>
    )
  }

  // ── Page ────────────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-surface p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <header className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-display text-on-surface">Listas de Produtos</h1>
            <p className="text-body-sm text-on-surface-variant mt-1">
              Groupe seus produtos em listas.
            </p>
          </div>
          <button
            onClick={() => {
              setEditingList(null)
              setModalOpen(true)
            }}
            className="px-4 py-2 rounded bg-accent text-on-accent text-sm font-medium hover:bg-accent/90 transition-colors flex items-center gap-2"
          >
            <PlusIcon />
            Nova lista
          </button>
        </header>

        {/* Lists */}
        {lists.length === 0 ? (
          <div className="bg-surface-container rounded-lg p-12 text-center">
            <p className="text-on-surface-variant text-sm">Nenhuma lista criada.</p>
            <button
              onClick={() => {
                setEditingList(null)
                setModalOpen(true)
              }}
              className="mt-4 px-4 py-2 rounded bg-accent text-on-accent text-sm"
            >
              Criar primeira lista
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {lists.map((list) => (
              <div
                key={list.id}
                className="bg-surface-container rounded-lg p-4 border border-white/5 hover:border-white/10 transition-colors"
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <h3 className="text-on-surface font-medium truncate">{list.name}</h3>
                    <p className="text-body-sm text-on-surface-variant mt-1">
                      {list.products?.length ?? 0} produto{list.products && list.products.length !== 1 ? "s" : ""}
                      {" · "}
                      {new Date(list.created_at).toLocaleDateString("pt-BR")}
                      {" · "}
                      {list.products?.length ? (
                        <span className="text-accent">
                          {list.products.map((p) => p.name).join(", ")}
                        </span>
                      ) : "vazio"}
                    </p>
                  </div>
                  <button
                    onClick={() => setDeleteConfirm(list.id)}
                    className="p-1.5 rounded hover:bg-red-500/20 transition-colors text-red-400 shrink-0"
                    title="Remover lista"
                  >
                    <TrashIcon />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create modal */}
      {modalOpen && (
        <ListModal
          list={editingList}
          onClose={() => {
            setModalOpen(false)
            setEditingList(null)
          }}
          onSave={(name) => handleCreate(name)}
          loading={createMutation.isPending}
        />
      )}

      {/* Delete confirmation modal */}
      {deleteConfirm != null && (
        <DeleteModal
          listId={deleteConfirm}
          onClose={() => setDeleteConfirm(null)}
          onConfirm={() => handleDelete(deleteConfirm)}
          loading={deleteMutation.isPending}
        />
      )}
    </div>
  )
}

// ── List Modal (create / edit) ────────────────────────────────────────────────────

interface ListModalProps {
  list: ProductList | null
  onClose: () => void
  onSave: (name: string) => void
  loading: boolean
}

function ListModal({ list, onClose, onSave, loading }: ListModalProps) {
  const [name, setName] = useState(list?.name ?? "")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (name.trim()) {
      onSave(name.trim())
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-surface rounded-xl shadow-xl max-w-sm w-full p-6">
        <h2 className="text-xl font-display text-on-surface mb-2">
          {list ? "Editar lista" : "Nova lista"}
        </h2>
        <p className="text-body-sm text-on-surface-variant mb-6">
          {list ? "Altere o nome da lista." : "Digite um nome para a nova lista."}
        </p>
        <form onSubmit={handleSubmit}>
          <label className="block text-label-caps text-on-surface-variant mb-1">
            Nome *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full px-3 py-2 rounded bg-surface-container border border-white/10 text-on-surface focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <div className="flex justify-end gap-3 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded text-on-surface-variant hover:bg-white/5 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="px-4 py-2 rounded bg-accent text-on-accent text-sm font-medium hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "Salvando..." : list ? "Salvar" : "Criar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Delete confirmation modal ────────────────────────────────────────────────────

interface DeleteModalProps {
  listId: number
  onClose: () => void
  onConfirm: () => void
  loading: boolean
}

function DeleteModal({ listId, onClose, onConfirm, loading }: DeleteModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-surface rounded-xl shadow-xl max-w-sm w-full p-6">
        <h2 className="text-xl font-display text-on-surface mb-2">Confirmar remoção</h2>
        <p className="text-body-sm text-on-surface-variant mb-6">
          Tem certeza que deseja remover esta lista? Esta ação não pode ser desfeita.
        </p>
        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded text-on-surface-variant hover:bg-white/5 transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="px-4 py-2 rounded bg-red-500 text-white text-sm font-medium hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? "Removendo..." : "Remover"}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Ícones SVG inline ────────────────────────────────────────────────────────────

function PlusIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      width="16"
      height="16"
      className="inline-block"
    >
      <path d="M3 3h18v18H3V3zm2 2v14h14V5H5zm3 5h4v2h-4V10zm0 4h4v2h-4v-2z" />
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      width="16"
      height="16"
      className="inline-block"
    >
      <path d="M3 3h18v18H3V3zm2 2v14h14V5H5zm2 2h8v2H7V7zm0 4h6v2H7v-2z" />
    </svg>
  )
}
