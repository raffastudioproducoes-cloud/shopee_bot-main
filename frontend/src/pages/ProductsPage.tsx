import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, useCallback } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import { productsApi, type Product } from "../api/products"
import { Plus, Edit, Trash2, Search, Loader2 } from "lucide-react"

export function ProductsPage() {
  const { isAuthenticated, logout } = useAuthStore()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState("")
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState({
    name: "",
    product_id: "",
    original_link: "",
    commission_link: "",
    commission: "",
    image: "",
    price_min: "",
    price_max: "",
  })
  const [deleteId, setDeleteId] = useState<number | null>(null)

  // ── Query ──────────────────────────────────────────────────────────────────────

  const { data, isLoading, error } = useQuery({
    queryKey: ["products", search],
    queryFn: () => productsApi.list({ search: search || undefined }),
  })

  const products = data?.data ?? []

  // ── Mutations ──────────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: (body: Omit<Product, 'id' | 'user_id' | 'created_at' | 'updated_at'>) =>
      productsApi.create(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] })
      setModalOpen(false)
      setForm({ name: "", product_id: "", original_link: "", commission_link: "", commission: "", image: "", price_min: "", price_max: "" })
    },
    onError: (err: Error) => {
      if (err.message.includes("401") || err.message === "Não autenticado") {
        logout()
        router.navigate({ to: "/login" })
      }
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<Product> }) =>
      productsApi.update(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] })
      setEditingId(null)
      setModalOpen(false)
      setForm({ name: "", product_id: "", original_link: "", commission_link: "", commission: "", image: "", price_min: "", price_max: "" })
    },
    onError: (err: Error) => {
      if (err.message.includes("401") || err.message === "Não autenticado") {
        logout()
        router.navigate({ to: "/login" })
      }
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => productsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] })
      setDeleteId(null)
    },
    onError: (err: Error) => {
      if (err.message.includes("401") || err.message === "Não autenticado") {
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
        category: null,
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

  const handleEdit = useCallback((product: Product) => {
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
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto">
          <div className="animate-pulse space-y-4">
            <div className="h-8 w-48 bg-gray-200 rounded" />
            <div className="h-96 bg-gray-200 rounded" />
          </div>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto text-center py-12">
          <p className="text-gray-500">Não autenticado.</p>
          <button
            onClick={() => router.navigate({ to: "/login" })}
            className="mt-4 px-4 py-2 rounded bg-primary text-white"
          >
            Ir para login
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <header className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Produtos</h1>
            <p className="text-gray-500 mt-1">Catálogo de produtos da Shopee.</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar produtos..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-64 pl-10 pr-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
              />
            </div>
            <button
              onClick={() => {
                setEditingId(null)
                setForm({ name: "", product_id: "", original_link: "", commission_link: "", commission: "", image: "", price_min: "", price_max: "" })
                setModalOpen(true)
              }}
              className="px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover transition flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Novo produto
            </button>
          </div>
        </header>

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
            {error.message}
          </div>
        )}

        {/* Products table */}
        {products.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <p className="text-gray-500 text-sm">Nenhum produto cadastrado.</p>
            <button
              onClick={() => {
                setEditingId(null)
                setForm({ name: "", product_id: "", original_link: "", commission_link: "", commission: "", image: "", price_min: "", price_max: "" })
                setModalOpen(true)
              }}
              className="mt-4 px-4 py-2 rounded-lg bg-primary text-white text-sm"
            >
              Cadastrar primeiro produto
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 bg-gray-50">
                    <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider py-3 px-4">Nome</th>
                    <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider py-3 px-4">ID Shopee</th>
                    <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider py-3 px-4">Comissão</th>
                    <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider py-3 px-4">Preço</th>
                    <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider py-3 px-4">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((product: Product) => (
                    <tr key={product.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-3">
                          {product.image && (
                            <img
                              src={product.image}
                              alt=""
                              className="w-10 h-10 rounded object-cover bg-gray-100 shrink-0"
                            />
                          )}
                          <span className="text-gray-900 font-medium truncate max-w-[200px]">{product.name}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-gray-500 font-mono text-xs">{product.product_id}</td>
                      <td className="py-3 px-4 text-right text-gray-500">
                        {product.commission != null ? `${product.commission}%` : "—"}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-500">
                        {product.price_min != null && product.price_max != null ? (
                          <span className="font-mono">R$ {product.price_min.toFixed(2)} – R$ {product.price_max.toFixed(2)}</span>
                        ) : product.price_min != null ? (
                          <span className="font-mono">R$ {product.price_min.toFixed(2)}+</span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleEdit(product)}
                            className="p-1.5 rounded hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-700"
                            title="Editar"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setDeleteId(product.id)}
                            className="p-1.5 rounded hover:bg-red-50 transition-colors text-red-500"
                            title="Remover"
                          >
                            <Trash2 className="w-4 h-4" />
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
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-900">{editingId ? "Editar produto" : "Novo produto"}</h2>
              <p className="text-gray-500 text-sm mt-1">
                {editingId ? "Altere os dados do produto." : "Preencha os dados do produto."}
              </p>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault()
                editingId ? handleUpdate() : handleCreate()
              }}
              className="p-6 space-y-4"
            >
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Nome *</label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                    required
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">ID Shopee *</label>
                  <input
                    type="text"
                    value={form.product_id}
                    onChange={(e) => setForm((f) => ({ ...f, product_id: e.target.value }))}
                    required
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Link original</label>
                <input
                  type="url"
                  value={form.original_link}
                  onChange={(e) => setForm((f) => ({ ...f, original_link: e.target.value }))}
                  placeholder="https://..."
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Link de comissão</label>
                <input
                  type="url"
                  value={form.commission_link}
                  onChange={(e) => setForm((f) => ({ ...f, commission_link: e.target.value }))}
                  placeholder="https://..."
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Comissão (%)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.commission}
                    onChange={(e) => setForm((f) => ({ ...f, commission: e.target.value }))}
                    placeholder="0"
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Imagem</label>
                  <input
                    type="url"
                    value={form.image}
                    onChange={(e) => setForm((f) => ({ ...f, image: e.target.value }))}
                    placeholder="https://..."
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Preço mínimo (R$)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.price_min}
                    onChange={(e) => setForm((f) => ({ ...f, price_min: e.target.value }))}
                    placeholder="0.00"
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Preço máximo (R$)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.price_max}
                    onChange={(e) => setForm((f) => ({ ...f, price_max: e.target.value }))}
                    placeholder="0.00"
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={handleCancel}
                  className="px-4 py-2 rounded-lg text-gray-600 hover:bg-gray-100 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition"
                >
                  {createMutation.isPending || updateMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      Salvando...
                    </>
                  ) : editingId ? (
                    "Salvar"
                  ) : (
                    "Criar"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal de exclusão */}
      {deleteId != null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-sm w-full p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-2">Confirmar remoção</h2>
            <p className="text-gray-500 text-sm mb-6">
              Tem certeza que deseja remover este produto? Esta ação não pode ser desfeita.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteId(null)}
                className="px-4 py-2 rounded-lg text-gray-600 hover:bg-gray-100 transition"
              >
                Cancelar
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 rounded-lg bg-red-500 text-white text-sm font-medium hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
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