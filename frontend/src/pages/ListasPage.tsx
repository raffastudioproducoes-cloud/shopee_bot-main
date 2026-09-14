import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, useCallback } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import { listsApi, type ProductList, type ProductListsResponse } from "../api/lists"
import { Plus, Trash2 } from "lucide-react"

export function ListasPage() {
  const { logout } = useAuthStore()
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingList, setEditingList] = useState<ProductList | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)

  const { data: listsData, isLoading } = useQuery<ProductListsResponse>({
    queryKey: ["lists"],
    queryFn: () => listsApi.list(),
  })

  const lists = listsData?.data ?? []

  // ── Create mutation ─────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: (name: string) => listsApi.create({ name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lists"] })
      setModalOpen(false)
    },
    onError: (err: Error) => {
      if (err.message.includes("401") || err.message === "Não autenticado") {
        logout()
        router.navigate({ to: "/login" })
      }
    },
  })

  // ── Update mutation ─────────────────────────────────────────────────────────────

  const updateMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => listsApi.update(id, { name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lists"] })
      setModalOpen(false)
      setEditingList(null)
    },
    onError: (err: Error) => {
      if (err.message.includes("401") || err.message === "Não autenticado") {
        logout()
        router.navigate({ to: "/login" })
      }
    },
  })

  // ── Delete mutation ─────────────────────────────────────────────────────────────

  const deleteMutation = useMutation({
    mutationFn: (id: number) => listsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lists"] })
      setDeleteConfirm(null)
    },
    onError: (err: Error) => {
      if (err.message.includes("401") || err.message === "Não autenticado") {
        logout()
        router.navigate({ to: "/login" })
      }
    },
  })

  // ── Handlers ────────────────────────────────────────────────────────────────────

  const handleCreate = useCallback(
    (name: string) => {
      if (editingList) {
        updateMutation.mutate({ id: editingList.id, name })
      } else {
        createMutation.mutate(name)
      }
    },
    [editingList, createMutation, updateMutation],
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
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="animate-pulse space-y-4">
            <div className="h-8 w-40 bg-gray-200 rounded" />
            <div className="h-96 bg-gray-200 rounded" />
          </div>
        </div>
      </div>
    )
  }

  if (!listsData) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto text-center py-12">
          <p className="text-gray-500">Erro ao carregar as listas.</p>
          <button
            onClick={() => router.navigate({ to: "/login" })}
            className="mt-4 px-4 py-2 rounded bg-primary text-white"
          >
            Voltar ao login
          </button>
        </div>
      </div>
    )
  }

  // ── Page ────────────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <header className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Listas de Produtos</h1>
            <p className="text-gray-500 mt-1">Agrupe seus produtos em listas.</p>
          </div>
          <button
            onClick={() => {
              setEditingList(null)
              setModalOpen(true)
            }}
            className="px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover transition flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Nova lista
          </button>
        </header>

        {/* Lists */}
        {lists.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <p className="text-gray-500 text-sm">Nenhuma lista criada.</p>
            <button
              onClick={() => {
                setEditingList(null)
                setModalOpen(true)
              }}
              className="mt-4 px-4 py-2 rounded-lg bg-primary text-white text-sm"
            >
              Criar primeira lista
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {lists.map((list) => (
              <div
                key={list.id}
                className="bg-white rounded-xl border border-gray-200 p-4 hover:border-gray-300 transition-colors"
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <h3 className="text-gray-900 font-medium truncate">{list.name}</h3>
                    <p className="text-gray-500 text-sm mt-1">
                      {list.product_count ?? 0} produto{list.product_count !== 1 ? "s" : ""}
                      {" · "}
                      {new Date(list.created_at).toLocaleDateString("pt-BR")}
                    </p>
                  </div>
                  <button
                    onClick={() => setDeleteConfirm(list.id)}
                    className="p-1.5 rounded hover:bg-red-50 transition-colors text-red-500 shrink-0"
                    title="Remover lista"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create/Edit modal */}
      {modalOpen && (
        <ListModal
          list={editingList}
          onClose={() => {
            setModalOpen(false)
            setEditingList(null)
          }}
          onSave={handleCreate}
          loading={createMutation.isPending || updateMutation.isPending}
        />
      )}

      {/* Delete confirmation modal */}
      {deleteConfirm != null && (
        <DeleteModal
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
      <div className="bg-white rounded-xl shadow-xl max-w-sm w-full p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-2">
          {list ? "Editar lista" : "Nova lista"}
        </h2>
        <p className="text-gray-500 text-sm mb-6">
          {list ? "Altere o nome da lista." : "Digite um nome para a nova lista."}
        </p>
        <form onSubmit={handleSubmit}>
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
            Nome *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
          />
          <div className="flex justify-end gap-3 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-gray-600 hover:bg-gray-100 transition"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition"
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
  onClose: () => void
  onConfirm: () => void
  loading: boolean
}

function DeleteModal({ onClose, onConfirm, loading }: DeleteModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-sm w-full p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-2">Confirmar remoção</h2>
        <p className="text-gray-500 text-sm mb-6">
          Tem certeza que deseja remover esta lista? Esta ação não pode ser desfeita.
        </p>
        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-gray-600 hover:bg-gray-100 transition"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="px-4 py-2 rounded-lg bg-red-500 text-white text-sm font-medium hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {loading ? "Removendo..." : "Remover"}
          </button>
        </div>
      </div>
    </div>
  )
}