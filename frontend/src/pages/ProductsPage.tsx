import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, useCallback } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"

// ── ProductsPage ────────────────────────────────────────────────────────────────

export function ProductsPage() {
  const { accessToken, logout } = useAuthStore()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState("")
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState({ name: "", product_id: "", original_link: "", commission_link: "", commission: "", image: "", price_min: "", price_max: "" })
  const [deleteId, setDeleteId] = useState<number | null>(null)

  // ── Query ──────────────────────────────────────────────────────────────────────

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["products", search],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (search) params.set("search", search)
      const res = await fetch(`/api/products/?${params}`, {
        credentials: "include",
      })
      if (!res.ok) {
        if (res.status === 401) {
          logout()
          throw new Error("Não autenticado")
        }
        throw new Error("Falha ao buscar produtos")
      }
      return res.json()
    },
  })

  const products = data?.data ?? []
  const isPending = false // placeholder

  // ── Mutations ──────────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: async (body: any) => {
      const res = await fetch("/api/products/", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error("Falha ao criar produto")
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] })
      setModalOpen(false)
      setForm({ name: "", product_id: "", original_link: "", commission_link: "", commission: "", image: "", price_min: "", price_max: "" })
    },
    onError: (err: Error) => {
      if (err.message === "Não autenticado") {
        logout()
        router.navigate({ to: "/login" })
      }
    },
  })

  const updateMutation = useMutation({
    mutationFn: async ({ id, body }: { id: number; body: any }) => {
      const res = await fetch(`/api/products/${id}`, {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error("Falha ao atualizar produto")
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] })
      setEditingId(null)
      setModalOpen(false)
      setForm({ name: "", product_id: "", original_link: "", commission_link: "", commission: "", image: "", price_min: "", price_max: "" })
    },
    onError: (err: Error) => {
      if (err.message === "Não autenticado") {
        logout()
        router.navigate({ to: "/login" })
      }
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await fetch(`/api/products/${id}`, {
        method: "DELETE",
        credentials: "include",
      })
      if (!res.ok) throw new Error("Falha ao remover produto")
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] })
      setDeleteId(null)
    },
    onError: (err: Error) => {
      if (err.message === "Não autenticado") {
        logout()
        router.navigate({ to: "/login" })
      }
    },
  })

  // ── Handlers ───────────────────────────────────────────────────────────────────

  const handleCreate = useCallback(() => {
    createMutation.mutate({
      name: form.name,
      product_id: form.product_id,
      original_link: form.original_link || null,
      commission_link: form.commission_link || null,
      commission: form.commission ? Number(form.commission) : null,
      image: form.image || null,
      price_min: form.price_min ? Number(form.price_min) : null,
      price_max: form.price_max ? Number(form.price_max) : null,
    })
  }, [form, createMutation])

  const handleUpdate = useCallback(() => {
    if (!editingId) return
    updateMutation.mutate({
      id: editingId,
      body: {
        name: form.name,
        product_id: form.product_id,
        original_link: form.original_link || null,
        commission_link: form.commission_link || null,
        commission: form.commission ? Number(form.commission) : null,
        image: form.image || null,
        price_min: form.price_min ? Number(form.price_min) : null,
        price_max: form.price_max ? Number(form.price_max) : null,
      },
    })
  }, [form, editingId, updateMutation])

  const handleDelete = useCallback(() => {
    if (deleteId) deleteMutation.mutate(deleteId)
  }, [deleteId, deleteMutation])

  const handleEdit = useCallback((product: any) => {
    setEditingId(product.id)
    setForm({
      name: product.name || "",
      product_id: product.product_id || "",
      original_link: product.original_link || "",
      commission_link: product.commission_link || "",
      commission: product.commission != null ? String(product.commission) : "",
      image: product.image || "",
      price_min: product.price_min != null ? String(product.price_min) : "",
      price_max: product.price_max != null ? String(product.price_max) : "",
    })
    setModalOpen(true)
  }, [])

  const handleCancel = useCallback(() => {
    setModalOpen(false)
    setEditingId(null)
    setForm({ name: "", product_id: "", original_link: "", commission_link: "", commission: "", image: "", price_min: "", price_max: "" })
  }, [])

  // ── Render ────────────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="min-h-screen bg-surface p-6">
        <div className="max-w-6xl mx-auto">
          <div className="animate-pulse space-y-4">
            <div className="h-8 w-48 bg-surface-container rounded" />
            <div className="h-96 bg-surface-container rounded" />
          </div>
        </div>
      </div>
    )
  }

  if (!accessToken) {
    return (
      <div className="min-h-screen bg-surface p-6">
        <div className="max-w-6xl mx-auto text-center py-12">
          <p className="text-on-surface-variant">Não autenticado.</p>
          <button
            onClick={() => router.navigate({ to: "/login" })}
            className="mt-4 px-4 py-2 rounded bg-accent text-on-accent"
          >
            Ir para login
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-surface p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <header className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-display text-on-surface">Produtos</h1>
            <p className="text-body-sm text-on-surface-variant mt-1">
              Catálogo de produtos da Shopee.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="text"
              placeholder="Buscar produtos..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="px-3 py-2 rounded bg-surface-container border border-white/10 text-on-surface w-48 focus:outline-none focus:ring-2 focus:ring-accent"
            />
            <button
              onClick={() => {
                setEditingId(null)
                setForm({ name: "", product_id: "", original_link: "", commission_link: "", commission: "", image: "", price_min: "", price_max: "" })
                setModalOpen(true)
              }}
              className="px-4 py-2 rounded bg-accent text-on-accent text-sm font-medium hover:bg-accent/90 transition-colors flex items-center gap-2"
            >
              <PlusIcon />
              Novo produto
            </button>
          </div>
        </header>

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 rounded bg-red-500/20 text-red-400 text-sm">
            {error.message}
          </div>
        )}

        {/* Products table */}
        {products.length === 0 ? (
          <div className="bg-surface-container rounded-lg p-12 text-center">
            <p className="text-on-surface-variant text-sm">Nenhum produto cadastrado.</p>
            <button
              onClick={() => {
                setEditingId(null)
                setForm({ name: "", product_id: "", original_link: "", commission_link: "", commission: "", image: "", price_min: "", price_max: "" })
                setModalOpen(true)
              }}
              className="mt-4 px-4 py-2 rounded bg-accent text-on-accent text-sm"
            >
              Cadastrar primeiro produto
            </button>
          </div>
        ) : (
          <div className="bg-surface-container rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="text-left text-label-caps text-on-surface-variant py-3 px-4 font-medium">
                      Nome
                    </th>
                    <th className="text-left text-label-caps text-on-surface-variant py-3 px-4 font-medium">
                      ID Shopee
                    </th>
                    <th className="text-right text-label-caps text-on-surface-variant py-3 px-4 font-medium">
                      Comissão
                    </th>
                    <th className="text-right text-label-caps text-on-surface-variant py-3 px-4 font-medium">
                      Preço
                    </th>
                    <th className="text-right text-label-caps text-on-surface-variant py-3 px-4 font-medium">
                      Ações
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((product: any) => (
                    <tr
                      key={product.id}
                      className="border-b border-white/5 hover:bg-white/[0.02] transition-colors"
                    >
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-3">
                          {product.image && (
                            <img
                              src={product.image}
                              alt=""
                              className="w-10 h-10 rounded object-cover bg-surface-container-high shrink-0"
                            />
                          )}
                          <span className="text-on-surface font-medium truncate max-w-[200px]">
                            {product.name}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-on-surface-variant font-mono text-xs">
                        {product.product_id}
                      </td>
                      <td className="py-3 px-4 text-right text-on-surface-variant">
                        {product.commission != null ? `${product.commission}%` : "—"}
                      </td>
                      <td className="py-3 px-4 text-right text-on-surface-variant">
                        {product.price_min != null && product.price_max != null ? (
                          <span className="font-mono">
                            R$ {product.price_min.toFixed(2)} – R$ {product.price_max.toFixed(2)}
                          </span>
                        ) : product.price_min != null ? (
                          <span className="font-mono">
                            R$ {product.price_min.toFixed(2)}+{" "}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleEdit(product)}
                            className="p-1.5 rounded hover:bg-white/10 transition-colors"
                            title="Editar"
                          >
                            <EditIcon />
                          </button>
                          <button
                            onClick={() => setDeleteId(product.id)}
                            className="p-1.5 rounded hover:bg-red-500/20 transition-colors text-red-400"
                            title="Remover"
                          >
                            <TrashIcon />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Modal de criação/edição */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-surface rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-white/5">
              <h2 className="text-xl font-display text-on-surface">
                {editingId ? "Editar produto" : "Novo produto"}
              </h2>
              <p className="text-body-sm text-on-surface-variant mt-1">
                {editingId
                  ? "Altere os dados do produto."
                  : "Preencha os dados do produto."}
              </p>
            </div>

            <form onSubmit={(e) => { e.preventDefault(); editingId ? handleUpdate() : handleCreate(); }} className="p-6 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-label-caps text-on-surface-variant mb-1">Nome *</label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                    required
                    className="w-full px-3 py-2 rounded bg-surface-container border border-white/10 text-on-surface focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                </div>
                <div>
                  <label className="block text-label-caps text-on-surface-variant mb-1">ID Shopee *</label>
                  <input
                    type="text"
                    value={form.product_id}
                    onChange={(e) => setForm((f) => ({ ...f, product_id: e.target.value }))}
                    required
                    className="w-full px-3 py-2 rounded bg-surface-container border border-white/10 text-on-surface font-mono focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                </div>
              </div>

              <div>
                <label className="block text-label-caps text-on-surface-variant mb-1">Link original</label>
                <input
                  type="url"
                  value={form.original_link}
                  onChange={(e) => setForm((f) => ({ ...f, original_link: e.target.value }))}
                  placeholder="https://..."
                  className="w-full px-3 py-2 rounded bg-surface-container border border-white/10 text-on-surface focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>

              <div>
                <label className="block text-label-caps text-on-surface-variant mb-1">Link de comissão</label>
                <input
                  type="url"
                  value={form.commission_link}
                  onChange={(e) => setForm((f) => ({ ...f, commission_link: e.target.value }))}
                  placeholder="https://..."
                  className="w-full px-3 py-2 rounded bg-surface-container border border-white/10 text-on-surface focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-label-caps text-on-surface-variant mb-1">Comissão (%)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.commission}
                    onChange={(e) => setForm((f) => ({ ...f, commission: e.target.value }))}
                    placeholder="0"
                    className="w-full px-3 py-2 rounded bg-surface-container border border-white/10 text-on-surface focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                </div>
                <div>
                  <label className="block text-label-caps text-on-surface-variant mb-1">Imagem</label>
                  <input
                    type="url"
                    value={form.image}
                    onChange={(e) => setForm((f) => ({ ...f, image: e.target.value }))}
                    placeholder="https://..."
                    className="w-full px-3 py-2 rounded bg-surface-container border border-white/10 text-on-surface focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-label-caps text-on-surface-variant mb-1">Preço mínimo (R$)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.price_min}
                    onChange={(e) => setForm((f) => ({ ...f, price_min: e.target.value }))}
                    placeholder="0.00"
                    className="w-full px-3 py-2 rounded bg-surface-container border border-white/10 text-on-surface focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                </div>
                <div>
                  <label className="block text-label-caps text-on-surface-variant mb-1">Preço máximo (R$)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.price_max}
                    onChange={(e) => setForm((f) => ({ ...f, price_max: e.target.value }))}
                    placeholder="0.00"
                    className="w-full px-3 py-2 rounded bg-surface-container border border-white/10 text-on-surface focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={handleCancel}
                  className="px-4 py-2 rounded text-on-surface-variant hover:bg-white/5 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="px-4 py-2 rounded bg-accent text-on-accent text-sm font-medium hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {createMutation.isPending || updateMutation.isPending ? "Salvando..." : editingId ? "Salvar" : "Criar"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal de exclusão */}
      {deleteId != null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-surface rounded-xl shadow-xl max-w-sm w-full p-6">
            <h2 className="text-xl font-display text-on-surface mb-2">Confirmar remoção</h2>
            <p className="text-body-sm text-on-surface-variant mb-6">
              Tem certeza que deseja remover este produto? Esta ação não pode ser desfeita.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteId(null)}
                className="px-4 py-2 rounded text-on-surface-variant hover:bg-white/5 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 rounded bg-red-500 text-white text-sm font-medium hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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

function EditIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      width="16"
      height="16"
      className="inline-block"
    >
      <path d="M3 3h18v18H3V3zm2 2v14h14V5H5zm2 2h2v2H7V7zm0 4h2v2H7v-2zm0 4h2v2H7v-2z" />
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
