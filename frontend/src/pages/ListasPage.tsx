import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, useCallback } from "react"
import { useAuthStore } from "../stores/authStore"
import { router } from "../router"
import { listsApi, type ProductList, type ProductListsResponse } from "../api/lists"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { IconButton } from "../components/ui/IconButton"
import { TextInput } from "../components/ui/TextInput"
import { Modal } from "../components/ui/Modal"
import { TimelineListCard } from "../components/ui/TimelineListCard"
import { Icon } from "../components/ui/Icon"

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
    mutationFn: (name: string) => listsApi.create({ name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lists"] })
      setModalOpen(false)
    },
    onError: onAuthError,
  })

  // ── Update mutation ─────────────────────────────────────────────────────────────

  const updateMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => listsApi.update(id, { name }),
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lists"] })
      setDeleteConfirm(null)
    },
    onError: onAuthError,
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
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
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
    <Modal open onClose={onClose} title={list ? "Editar lista" : "Nova lista"} width={400}>
      <p style={{ color: "var(--text-muted)", font: "var(--text-role-body)", marginTop: 0, marginBottom: 16 }}>
        {list ? "Altere o nome da lista." : "Digite um nome para a nova lista."}
      </p>
      <form onSubmit={handleSubmit}>
        <TextInput label="Nome *" value={name} onChange={(e) => setName(e.target.value)} required />
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
