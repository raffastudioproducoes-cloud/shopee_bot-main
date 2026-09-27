import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, useCallback } from "react"
import type { CSSProperties } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import { productsApi, type Product } from "../api/products"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { IconButton } from "../components/ui/IconButton"
import { TextInput } from "../components/ui/TextInput"
import { Modal } from "../components/ui/Modal"
import { SearchField } from "../components/ui/SearchField"

const emptyForm = {
  name: "",
  product_id: "",
  original_link: "",
  commission_link: "",
  commission: "",
  image: "",
  price_min: "",
  price_max: "",
}

const thStyle: CSSProperties = {
  textAlign: "left",
  font: "var(--text-role-label)",
  letterSpacing: "var(--ls-label)",
  textTransform: "uppercase",
  color: "var(--text-muted)",
  padding: "12px 16px",
}

const tdStyle: CSSProperties = {
  padding: "12px 16px",
  font: "var(--text-role-body)",
  color: "var(--text-body)",
}

export function ProductsPage() {
  const { isAuthenticated, logout } = useAuthStore()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState("")
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [deleteId, setDeleteId] = useState<number | null>(null)

  // ── Query ──────────────────────────────────────────────────────────────────────

  const { data, isLoading, error } = useQuery({
    queryKey: ["products", search],
    queryFn: () => productsApi.list({ search: search || undefined }),
  })

  const products = data?.data ?? []

  // ── Mutations ──────────────────────────────────────────────────────────────────

  const onAuthError = (err: Error) => {
    if (err.message.includes("401") || err.message === "Não autenticado") {
      logout()
      router.navigate({ to: "/login" })
    }
  }

  const createMutation = useMutation({
    mutationFn: (body: Omit<Product, 'id' | 'user_id' | 'created_at' | 'updated_at'>) =>
      productsApi.create(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] })
      setModalOpen(false)
      setForm(emptyForm)
    },
    onError: onAuthError,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<Product> }) =>
      productsApi.update(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] })
      setEditingId(null)
      setModalOpen(false)
      setForm(emptyForm)
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => productsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] })
      setDeleteId(null)
    },
    onError: onAuthError,
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
    setForm(emptyForm)
  }, [])

  const openCreateModal = useCallback(() => {
    setEditingId(null)
    setForm(emptyForm)
    setModalOpen(true)
  }, [])

  // ── Render ────────────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 256, color: "var(--text-muted)" }}>
        Carregando...
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div style={{ textAlign: "center", padding: "48px 0" }}>
        <p style={{ color: "var(--text-muted)" }}>Não autenticado.</p>
        <Button variant="primary" onClick={() => router.navigate({ to: "/login" })} style={{ marginTop: 16 }}>
          Ir para login
        </Button>
      </div>
    )
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap-column)" }}>
      {/* Header */}
      <header style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        <div>
          <h1 style={{ font: "var(--text-role-hero)", color: "var(--text-display)", margin: 0 }}>Produtos</h1>
          <p style={{ color: "var(--text-muted)", marginTop: 4 }}>Catálogo de produtos da Shopee.</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <SearchField
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar produtos..."
            width={240}
          />
          <Button variant="primary" icon="plus" onClick={openCreateModal}>
            Novo produto
          </Button>
        </div>
      </header>

      {/* Error */}
      {error && (
        <div
          style={{
            padding: "12px 16px",
            borderRadius: "var(--r-md)",
            border: "1px solid var(--negative)",
            color: "var(--negative)",
            font: "var(--text-role-body)",
          }}
        >
          {error.message}
        </div>
      )}

      {/* Products table */}
      {products.length === 0 ? (
        <Panel surface="dark" style={{ padding: "48px 16px", textAlign: "center" }}>
          <p style={{ color: "var(--text-muted)", font: "var(--text-role-body)", margin: 0 }}>Nenhum produto cadastrado.</p>
          <Button variant="primary" style={{ marginTop: 16 }} onClick={openCreateModal}>
            Cadastrar primeiro produto
          </Button>
        </Panel>
      ) : (
        <Panel surface="dark">
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-hairline)" }}>
                  <th style={thStyle}>Nome</th>
                  <th style={thStyle}>ID Shopee</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Comissão</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Preço</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Ações</th>
                </tr>
              </thead>
              <tbody>
                {products.map((product: Product) => (
                  <tr key={product.id} style={{ borderBottom: "1px solid var(--border-card)" }}>
                    <td style={tdStyle}>
                      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        {product.image && (
                          <img
                            src={product.image}
                            alt=""
                            style={{
                              width: 40,
                              height: 40,
                              borderRadius: "var(--r-md)",
                              objectFit: "cover",
                              background: "var(--surface-inset)",
                              flexShrink: 0,
                            }}
                          />
                        )}
                        <span
                          style={{
                            fontWeight: "var(--fw-medium)" as unknown as number,
                            color: "var(--text-display)",
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            maxWidth: 200,
                            display: "inline-block",
                          }}
                        >
                          {product.name}
                        </span>
                      </div>
                    </td>
                    <td style={{ ...tdStyle, color: "var(--text-muted)", fontFamily: "monospace", fontSize: "var(--fs-caption)" }}>
                      {product.product_id}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right", color: "var(--text-muted)" }}>
                      {product.commission != null ? `${product.commission}%` : "—"}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right", color: "var(--text-muted)" }}>
                      {product.price_min != null && product.price_max != null ? (
                        <span style={{ fontFamily: "monospace" }}>
                          R$ {product.price_min.toFixed(2)} – R$ {product.price_max.toFixed(2)}
                        </span>
                      ) : product.price_min != null ? (
                        <span style={{ fontFamily: "monospace" }}>R$ {product.price_min.toFixed(2)}+</span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 4 }}>
                        <IconButton icon="pencil" label="Editar" tone="plain" size={30} onClick={() => handleEdit(product)} />
                        <IconButton icon="trash-2" label="Remover" tone="plain" size={30} onClick={() => setDeleteId(product.id)} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {/* Modal de criação/edição */}
      <Modal open={modalOpen} onClose={handleCancel} title={editingId ? "Editar produto" : "Novo produto"} width={560}>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            editingId ? handleUpdate() : handleCreate()
          }}
          style={{ display: "flex", flexDirection: "column", gap: 16 }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <TextInput
              label="Nome *"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              required
            />
            <TextInput
              label="ID Shopee *"
              value={form.product_id}
              onChange={(e) => setForm((f) => ({ ...f, product_id: e.target.value }))}
              required
              inputStyle={{ fontFamily: "monospace" }}
            />
          </div>

          <TextInput
            label="Link original"
            type="url"
            value={form.original_link}
            onChange={(e) => setForm((f) => ({ ...f, original_link: e.target.value }))}
            placeholder="https://..."
          />

          <TextInput
            label="Link de comissão"
            type="url"
            value={form.commission_link}
            onChange={(e) => setForm((f) => ({ ...f, commission_link: e.target.value }))}
            placeholder="https://..."
          />

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <TextInput
              label="Comissão (%)"
              type="number"
              step="0.01"
              min="0"
              value={form.commission}
              onChange={(e) => setForm((f) => ({ ...f, commission: e.target.value }))}
              placeholder="0"
            />
            <TextInput
              label="Imagem"
              type="url"
              value={form.image}
              onChange={(e) => setForm((f) => ({ ...f, image: e.target.value }))}
              placeholder="https://..."
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <TextInput
              label="Preço mínimo (R$)"
              type="number"
              step="0.01"
              min="0"
              value={form.price_min}
              onChange={(e) => setForm((f) => ({ ...f, price_min: e.target.value }))}
              placeholder="0.00"
            />
            <TextInput
              label="Preço máximo (R$)"
              type="number"
              step="0.01"
              min="0"
              value={form.price_max}
              onChange={(e) => setForm((f) => ({ ...f, price_max: e.target.value }))}
              placeholder="0.00"
            />
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, marginTop: 8 }}>
            <Button type="button" variant="ghost" onClick={handleCancel}>
              Cancelar
            </Button>
            <Button type="submit" variant="primary" disabled={createMutation.isPending || updateMutation.isPending}>
              {createMutation.isPending || updateMutation.isPending ? "Salvando..." : editingId ? "Salvar" : "Criar"}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal de exclusão */}
      <Modal open={deleteId != null} onClose={() => setDeleteId(null)} title="Confirmar remoção" width={400}>
        <p style={{ color: "var(--text-muted)", font: "var(--text-role-body)", marginBottom: 20 }}>
          Tem certeza que deseja remover este produto? Esta ação não pode ser desfeita.
        </p>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 12 }}>
          <Button variant="ghost" onClick={() => setDeleteId(null)}>
            Cancelar
          </Button>
          <Button variant="send" onClick={handleDelete} disabled={deleteMutation.isPending}>
            {deleteMutation.isPending ? "Removendo..." : "Remover"}
          </Button>
        </div>
      </Modal>
    </div>
  )
}
