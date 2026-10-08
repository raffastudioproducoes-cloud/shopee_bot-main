import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, useCallback } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import { listsApi, type ProductList, type ProductListsResponse } from "../api/lists"
import { productsApi, type ProductsResponse } from "../api/products"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { IconButton } from "../components/ui/IconButton"
import { TextInput } from "../components/ui/TextInput"
import { Modal } from "../components/ui/Modal"
import { TimelineListCard } from "../components/ui/TimelineListCard"
import { Icon } from "../components/ui/Icon"
import { ViewSwitcher, useViewMode, viewContainerStyle } from "../components/ui/ViewSwitcher"

function estimatedListValue(list: ProductList): string {
  if (!list.products || list.products.length === 0) return "—"
  const total = list.products.reduce((acc, p) => acc + (p.price_min ?? 0), 0)
  return total > 0 ? `R$ ${total.toFixed(2)}` : "—"
}

export function ListasPage() {
  const { logout } = useAuthStore()
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingList, setEditingList] = useState<ProductList | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)
  const [view, setView] = useViewMode("lists-view")

  const { data: listsData, isLoading } = useQuery<ProductListsResponse>({
    queryKey: ["lists"],
    queryFn: () => listsApi.list(),
  })

  const lists = listsData?.data ?? []

  const onAuthError = (err: Error) => {
    if (err.message.includes("401") || err.message === "Não autenticado") {
      logout()
      router.navigate({ to: "/login" })
    }
  }

  // ── Create mutation ─────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    // Uma única chamada: o backend cria lista + produtos de forma atômica (sem lista vazia em caso de erro).
    mutationFn: ({ name, productIds }: { name: string; productIds?: number[] }) =>
      listsApi.create({ name, product_ids: productIds }),
    meta: {
      toast: {
        pending: "Criando lista…",
        success: (data: unknown) => {
          const n = (data as { product_count?: number } | undefined)?.product_count ?? 0
          return n > 0 ? `Lista criada com ${n} ${n === 1 ? "produto" : "produtos"}` : "Lista criada"
        },
        error: "Não foi possível criar a lista",
      },
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lists"] })
      setModalOpen(false)
    },
    onError: onAuthError,
  })

  // ── Update mutation ─────────────────────────────────────────────────────────────

  const updateMutation = useMutation({
    mutationFn: ({ id, name, productIds }: { id: number; name: string; productIds?: number[] }) =>
      listsApi.update(id, { name, product_ids: productIds }),
    meta: { toast: { pending: "Salvando lista…", success: "Lista atualizada", error: "Não foi possível salvar a lista" } },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lists"] })
      setModalOpen(false)
      setEditingList(null)
    },
    onError: onAuthError,
  })

  // ── Delete mutation ─────────────────────────────────────────────────────────────

  const deleteMutation = useMutation({
    mutationFn: (id: number) => listsApi.delete(id),
    meta: { toast: { pending: "Removendo lista…", success: "Lista removida", error: "Não foi possível remover a lista" } },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lists"] })
      setDeleteConfirm(null)
    },
    onError: onAuthError,
  })

  // ── Handlers ────────────────────────────────────────────────────────────────────

  const handleCreate = useCallback(
    (name: string, productIds?: number[]) => {
      if (editingList) {
        updateMutation.mutate({ id: editingList.id, name, productIds })
      } else {
        createMutation.mutate({ name, productIds })
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
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 256, color: "var(--text-muted)" }}>
        Carregando...
      </div>
    )
  }

  if (!listsData) {
    return (
      <div style={{ textAlign: "center", padding: "48px 0" }}>
        <p style={{ color: "var(--text-muted)" }}>Erro ao carregar as listas.</p>
        <Button variant="primary" onClick={() => router.navigate({ to: "/login" })} style={{ marginTop: 16 }}>
          Voltar ao login
        </Button>
      </div>
    )
  }

  // ── Page ────────────────────────────────────────────────────────────────────────

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap-column)" }}>
      {/* Header */}
      <header style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        <div>
          <h1 style={{ font: "var(--text-role-hero)", color: "var(--text-display)", margin: 0 }}>Listas de Produtos</h1>
          <p style={{ color: "var(--text-muted)", marginTop: 4 }}>Agrupe seus produtos em listas.</p>
          <div style={{ marginTop: 10 }}>
            <ViewSwitcher value={view} onChange={setView} />
          </div>
        </div>
        <Button
          variant="primary"
          icon="plus"
          onClick={() => {
            setEditingList(null)
            setModalOpen(true)
          }}
        >
          Nova lista
        </Button>
      </header>

      {/* Lists */}
      {lists.length === 0 ? (
        <Panel surface="dark" style={{ padding: "48px 16px", textAlign: "center" }}>
          <p style={{ color: "var(--text-muted)", font: "var(--text-role-body)", margin: 0 }}>Nenhuma lista criada.</p>
          <Button
            variant="primary"
            style={{ marginTop: 16 }}
            onClick={() => {
              setEditingList(null)
              setModalOpen(true)
            }}
          >
            Criar primeira lista
          </Button>
        </Panel>
      ) : (
        <div style={viewContainerStyle(view)}>
          {lists.map((list) => (
            <TimelineListCard
              key={list.id}
              title={list.name}
              subtitle={`${list.product_count ?? 0} produto${list.product_count !== 1 ? "s" : ""}`}
              thumbnail={
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: 40,
                    height: 40,
                    borderRadius: "var(--r-md)",
                    background: "var(--surface-inset)",
                    color: "var(--text-muted)",
                    flexShrink: 0,
                  }}
                >
                  <Icon name="sliders-horizontal" size={18} />
                </span>
              }
              actions={
                <>
                  <IconButton
                    icon="pencil"
                    label="Editar lista"
                    tone="plain"
                    size={30}
                    onClick={() => {
                      setEditingList(list)
                      setModalOpen(true)
                    }}
                  />
                  <IconButton
                    icon="trash-2"
                    label="Remover lista"
                    tone="plain"
                    size={30}
                    onClick={() => setDeleteConfirm(list.id)}
                  />
                </>
              }
              stats={[
                { icon: "package", label: "Produtos", value: list.product_count ?? 0 },
                { icon: "calendar", label: "Criada em", value: new Date(list.created_at).toLocaleDateString("pt-BR") },
                {
                  icon: "calendar",
                  label: "Atualizada",
                  value: list.updated_at ? new Date(list.updated_at).toLocaleDateString("pt-BR") : "—",
                },
                { icon: "dollar-sign", label: "Valor (mín.)", value: estimatedListValue(list) },
              ]}
              sections={[
                { label: "Lista", content: list.name },
                {
                  label: "Produtos",
                  category: `${list.product_count ?? 0} ${list.product_count === 1 ? "item" : "itens"}`,
                  content:
                    list.products && list.products.length > 0 ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                        {list.products.slice(0, 6).map((p) => (
                          <div key={p.id} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.name}</span>
                            <span style={{ color: "var(--text-muted)", flexShrink: 0 }}>
                              {p.price_min != null ? `R$ ${p.price_min.toFixed(2)}` : "—"}
                            </span>
                          </div>
                        ))}
                        {list.products.length > 6 ? (
                          <span style={{ color: "var(--text-muted)" }}>+{list.products.length - 6} mais</span>
                        ) : null}
                      </div>
                    ) : (
                      "Nenhum produto nesta lista."
                    ),
                },
                {
                  label: "Criada em",
                  category: "Data",
                  content: new Date(list.created_at).toLocaleString("pt-BR"),
                },
                {
                  label: "Atualizada em",
                  category: "Data",
                  content: list.updated_at ? new Date(list.updated_at).toLocaleString("pt-BR") : "Nunca atualizada",
                },
              ]}
            />
          ))}
        </div>
      )}

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
  onSave: (name: string, productIds?: number[]) => void
  loading: boolean
}

function ListModal({ list, onClose, onSave, loading }: ListModalProps) {
  const [name, setName] = useState(list?.name ?? "")
  const [selectedIds, setSelectedIds] = useState<Set<number>>(
    () => new Set((list?.products ?? []).map((p) => p.id)),
  )
  const [search, setSearch] = useState("")

  const { data: productsData } = useQuery<ProductsResponse>({
    queryKey: ["products", "for-list"],
    queryFn: () => productsApi.list({ page_size: 200 }),
  })

  const products = productsData?.data ?? []
  const filteredProducts = search.trim()
    ? products.filter((p) => p.name.toLowerCase().includes(search.trim().toLowerCase()))
    : products

  const toggleProduct = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (loading) return // evita criar a lista várias vezes em cliques repetidos
    if (name.trim()) {
      onSave(name.trim(), Array.from(selectedIds))
    }
  }

  return (
    <Modal open onClose={onClose} title={list ? "Editar lista" : "Nova lista"} width={440}>
      <p style={{ color: "var(--text-muted)", font: "var(--text-role-body)", marginTop: 0, marginBottom: 16 }}>
        {list ? "Altere o nome da lista e os produtos associados." : "Digite um nome e escolha os produtos da nova lista."}
      </p>
      <form onSubmit={handleSubmit}>
        <TextInput label="Nome *" value={name} onChange={(e) => setName(e.target.value)} required />

        {(
          <div style={{ marginTop: 16 }}>
            <span
              style={{
                display: "block",
                font: "var(--text-role-label)",
                letterSpacing: "var(--ls-label)",
                textTransform: "uppercase",
                color: "var(--text-muted)",
                marginBottom: 6,
              }}
            >
              Produtos
            </span>
            {products.length > 6 ? (
              <TextInput
                placeholder="Buscar produto..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ marginBottom: 8 }}
              />
            ) : null}
            <div
              style={{
                maxHeight: 240,
                overflowY: "auto",
                display: "flex",
                flexDirection: "column",
                gap: 6,
                border: "1px solid var(--border-hairline)",
                borderRadius: "var(--r-md)",
                padding: 8,
              }}
            >
              {filteredProducts.length === 0 ? (
                <span style={{ color: "var(--text-muted)", padding: 4 }}>Nenhum produto encontrado.</span>
              ) : (
                filteredProducts.map((p) => (
                  <label key={p.id} style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
                    <input type="checkbox" checked={selectedIds.has(p.id)} onChange={() => toggleProduct(p.id)} />
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.name}</span>
                  </label>
                ))
              )}
            </div>
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, marginTop: 20 }}>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" disabled={loading || !name.trim()}>
            {loading ? "Salvando..." : list ? "Salvar" : "Criar"}
          </Button>
        </div>
      </form>
    </Modal>
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
    <Modal open onClose={onClose} title="Confirmar remoção" width={400}>
      <p style={{ color: "var(--text-muted)", font: "var(--text-role-body)", marginBottom: 20 }}>
        Tem certeza que deseja remover esta lista? Esta ação não pode ser desfeita.
      </p>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 12 }}>
        <Button variant="ghost" onClick={onClose}>
          Cancelar
        </Button>
        <Button variant="send" onClick={onConfirm} disabled={loading}>
          {loading ? "Removendo..." : "Remover"}
        </Button>
      </div>
    </Modal>
  )
}
