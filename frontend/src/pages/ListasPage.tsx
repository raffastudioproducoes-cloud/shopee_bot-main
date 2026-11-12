import { scheduleUndoableDelete, useHiddenIds } from "../lib/undoableDelete"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, useCallback, useEffect } from "react"
import { useSearch } from "@tanstack/react-router"
import { useAuthStore } from "../stores/authStore"
import { useProfileStore } from "../stores/profileStore"
import { useListsSearchStore } from "../stores/listsSearchStore"
import { matchesScopedSearch } from "../lib/pageSearch"
import { formDraftKey, clearFormDraft } from "../lib/formDraftStorage"
import { useAutosavedDraft } from "../hooks/useAutosavedDraft"
import { router } from "../router"
import { listsApi, type ProductList, type ProductListsResponse, type ListUsageResponse } from "../api/lists"
import { DEFAULT_LIST_SORT, LIST_SORT_OPTIONS, isListSortMode, isUsageSort, sortProductLists, type ListSortMode } from "../lib/listSorting"
import { productsApi, type ProductsResponse } from "../api/products"
import { formatBRL, formatPriceRange, toNumber } from "../lib/commission"
import { ResourceQuotaBar } from "../components/plans/ProductQuotaBar"
import { usePlanUsage } from "../hooks/usePlanUsage"
import { resourceAtLimit } from "../lib/planPresentation"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { PageSkeleton } from "../components/ui/Skeleton"
import { IconButton } from "../components/ui/IconButton"
import { TextInput } from "../components/ui/TextInput"
import { Select } from "../components/ui/Select"
import { Modal } from "../components/ui/Modal"
import { TimelineListCard } from "../components/ui/TimelineListCard"
import { Icon } from "../components/ui/Icon"
import { ViewSwitcher, useViewMode, viewContainerStyle } from "../components/ui/ViewSwitcher"

function estimatedListValue(list: ProductList): string {
  if (!list.products || list.products.length === 0) return "—"
  const total = list.products.reduce((acc, p) => acc + (toNumber(p.price_min) ?? 0), 0)
  return total > 0 ? formatBRL(total) : "—"
}

export function ListasPage() {
  const { action } = useSearch({ strict: false })
  const { logout, user } = useAuthStore()
  const activeProfileId = useProfileStore((state) => state.activeProfileId)
  const queryClient = useQueryClient()
  const planQuery = usePlanUsage()
  const listsAtLimit = !planQuery.isError && resourceAtLimit(planQuery.data?.resources.lists)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingList, setEditingList] = useState<ProductList | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)
  const [view, setView] = useViewMode("lists-view")
  const [sortMode, setSortMode] = useState<ListSortMode>(() => {
    try {
      const saved = localStorage.getItem("lists-sort")
      if (isListSortMode(saved)) return saved
    } catch {
      // Preferência não persiste no modo privado.
    }
    return DEFAULT_LIST_SORT
  })
  const changeSortMode = (next: ListSortMode) => {
    setSortMode(next)
    try {
      localStorage.setItem("lists-sort", next)
    } catch {
      // A ordenação continua funcional na sessão.
    }
  }
  const listSearch = useListsSearchStore((state) => state.query)
  const clearListSearch = useListsSearchStore((state) => state.clear)

  useEffect(() => {
    if (action !== "create" || planQuery.isPending || planQuery.isError || !planQuery.data) return
    if (!listsAtLimit) {
      setEditingList(null)
      setModalOpen(true)
    }
    void router.navigate({ to: "/lists", search: {}, replace: true })
  }, [action, planQuery.isPending, planQuery.isError, planQuery.data, listsAtLimit])

  const { data: listsData, isLoading } = useQuery<ProductListsResponse>({
    queryKey: ["lists", user?.id, activeProfileId],
    // Cobre os tetos comerciais Free/Pro/Premium numa chamada (20/100 listas por perfil).
    queryFn: () => listsApi.list({ limit: 100 }),
  })

  const usageSortSelected = isUsageSort(sortMode)
  // Consultar histórico somente quando o usuário ordenar por campanhas ativadas.
  const usageQuery = useQuery<ListUsageResponse>({
    queryKey: ["lists-usage", user?.id, activeProfileId],
    queryFn: () => listsApi.usage(),
    enabled: usageSortSelected && Boolean(user?.id) && Boolean(listsData),
    staleTime: 60_000,
  })
  const hiddenListIds = useHiddenIds("lists")
  const lists = (listsData?.data ?? []).filter((list) => !hiddenListIds.has(String(list.id)))
  const filteredLists = listSearch.trim()
    ? lists.filter((list) => matchesScopedSearch([
        list.name, ...(list.products ?? []).flatMap((product) => [product.name, product.product_id]),
      ], listSearch))
    : lists
  const visibleLists = sortProductLists(filteredLists, sortMode, usageQuery.data?.counts)

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
      clearFormDraft(formDraftKey(user?.id, "list-create", activeProfileId))
      queryClient.invalidateQueries({ queryKey: ["lists"] })
      queryClient.invalidateQueries({ queryKey: ["plan-usage"] })
      setModalOpen(false)
    },
    onError: onAuthError,
  })

  // ── Update mutation ─────────────────────────────────────────────────────────────

  const updateMutation = useMutation({
    mutationFn: ({ id, name, productIds }: { id: number; name: string; productIds?: number[] }) =>
      listsApi.update(id, { name, product_ids: productIds }),
    meta: { toast: { pending: "Salvando lista…", success: "Lista atualizada", error: "Não foi possível salvar a lista" } },
    onSuccess: (_result, variables) => {
      clearFormDraft(formDraftKey(user?.id, `list-edit:${variables.id}`, activeProfileId))
      queryClient.invalidateQueries({ queryKey: ["lists"] })
      queryClient.invalidateQueries({ queryKey: ["plan-usage"] })
      setModalOpen(false)
      setEditingList(null)
    },
    onError: onAuthError,
  })

  // ── Delete mutation ─────────────────────────────────────────────────────────────

  // Exclusão com "Desfazer": a lista some na hora e só é apagada no servidor após 7 s.
  const deleteMutation = {
    isPending: false,
    mutate: (id: number) => {
      setDeleteConfirm(null)
      scheduleUndoableDelete({
        kind: "lists",
        id,
        message: "Lista removida",
        errorMessage: "Não foi possível remover a lista",
        run: (keepalive) => listsApi.delete(id, keepalive),
        onSettled: () => Promise.all([
          queryClient.invalidateQueries({ queryKey: ["lists"] }),
          queryClient.invalidateQueries({ queryKey: ["plan-usage"] }),
        ]),
      })
    },
  }

  // ── Handlers ────────────────────────────────────────────────────────────────────

  const handleCreate = useCallback(
    (name: string, productIds?: number[]) => {
      if (editingList) {
        updateMutation.mutate({ id: editingList.id, name, productIds })
      } else if (!listsAtLimit) {
        createMutation.mutate({ name, productIds })
      }
    },
    [editingList, createMutation, updateMutation, listsAtLimit],
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
      <PageSkeleton variant="cards" titleWidth="160px" subtitleWidth="240px" action toolbar count={3} />
    )
  }

  if (!listsData) {
    return (
      <div className="csp-s-0274">
        <p className="csp-s-0275">Erro ao carregar as listas.</p>
        <Button variant="primary" onClick={() => router.navigate({ to: "/login" })} style={{ marginTop: 16 }}>
          Voltar ao login
        </Button>
      </div>
    )
  }

  // ── Page ────────────────────────────────────────────────────────────────────────

  return (
    <div className="csp-s-0276">
      {/* Header */}
      <header className="lists-page-header" style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        <div>
          <h1 className="csp-s-0277">Listas de Produtos</h1>
          <p className="csp-s-0278">Agrupe seus produtos em listas.</p>
          <div className="csp-s-0279" style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-end", gap: 12 }}>
            <ViewSwitcher value={view} onChange={setView} />
            <Select
              label="ORDENAR LISTAS"
              width="min(100%, 270px)"
              value={sortMode}
              onChange={(event) => changeSortMode(event.target.value as ListSortMode)}
              options={LIST_SORT_OPTIONS}
            />
          </div>
        </div>
        <Button
          variant="primary"
          icon="plus"
          disabled={listsAtLimit}
          onClick={() => {
            setEditingList(null)
            setModalOpen(true)
          }}
        >
          Nova lista
        </Button>
      </header>

      <ResourceQuotaBar
        resource="lists"
        plan={planQuery.data}
        loading={planQuery.isPending}
        error={planQuery.isError}
        onUpgrade={() => void router.navigate({ to: "/planos", search: { de: "listas" } })}
      />
      {usageSortSelected && usageQuery.isPending && (
        <p role="status" style={{ color: "var(--text-muted)", marginBottom: 12 }}>
          Consultando as campanhas ativadas dessas listas...
        </p>
      )}
      {usageSortSelected && usageQuery.isError && (
        <p role="alert" style={{ color: "var(--text-muted)", display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
          Não foi possível obter os dados de uso. A ordenação por campanhas fica pendente.
          <Button variant="ghost" size="sm" onClick={() => void usageQuery.refetch()}>Tentar novamente</Button>
        </p>
      )}
      {/* Busca restrita às listas do perfil ativo e aos produtos nelas contidos. */}
      {listSearch.trim() && (
        <p role="status" style={{ color: "var(--text-muted)", display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
          {visibleLists.length} de {lists.length} lista(s) encontrada(s).
          <Button variant="ghost" size="sm" onClick={clearListSearch}>Limpar busca</Button>
        </p>
      )}
      {/* Lists */}
      {visibleLists.length === 0 ? (
        <Panel surface="dark" style={{ padding: "48px 16px", textAlign: "center" }}>
          <p className="csp-s-0280">{listSearch.trim() ? "Nenhuma lista corresponde à busca." : "Nenhuma lista criada."}</p>
          {!listSearch.trim() && (
            <Button
              variant="primary"
              style={{ marginTop: 16 }}
              disabled={listsAtLimit}
              onClick={() => {
                setEditingList(null)
                setModalOpen(true)
              }}
            >
              Criar primeira lista
            </Button>
          )}
        </Panel>
      ) : (
        <div style={viewContainerStyle(view)}>
          {visibleLists.map((list) => (
            <TimelineListCard
              key={list.id}
              title={list.name}
              subtitle={`${list.product_count ?? 0} produto${list.product_count !== 1 ? "s" : ""}`}
              thumbnail={
                <span
                  className="csp-s-0281"
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
                {
                  label: "Produtos",
                  category: `${list.product_count ?? 0} ${list.product_count === 1 ? "item" : "itens"}`,
                  content:
                    list.products && list.products.length > 0 ? (
                      <div className="csp-s-0282">
                        {list.products.slice(0, 6).map((p) => (
                          <div key={p.id} className="csp-s-0283">
                            <span className="csp-s-0284">{p.name}</span>
                            <span className="csp-s-0285">
                              {formatPriceRange(p.price_min, null)}
                            </span>
                          </div>
                        ))}
                        {list.products.length > 6 ? (
                          <span className="csp-s-0286">+{list.products.length - 6} mais</span>
                        ) : null}
                      </div>
                    ) : (
                      "Nenhum produto nesta lista."
                    ),
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
  const userId = useAuthStore((state) => state.user?.id)
  const activeProfileId = useProfileStore((state) => state.activeProfileId)
  const draftKey = formDraftKey(userId, list ? `list-edit:${list.id}` : "list-create", activeProfileId)
  useAutosavedDraft(draftKey, { name, selectedIds: Array.from(selectedIds), search }, (saved) => {
    setName(typeof saved?.name === "string" ? saved.name : (list?.name ?? ""))
    setSelectedIds(new Set(Array.isArray(saved?.selectedIds)
      ? saved.selectedIds.filter((id): id is number => typeof id === "number" && Number.isInteger(id))
      : (list?.products ?? []).map((p) => p.id)))
    setSearch(typeof saved?.search === "string" ? saved.search : "")
  })

  const { data: productsData } = useQuery<ProductsResponse>({
    queryKey: ["products", "for-list"],
    queryFn: () => productsApi.list({ page_size: 200 }),
  })

  const products = productsData?.data ?? []
  const filteredProducts = search.trim()
    ? products.filter((product) => matchesScopedSearch([product.name, product.product_id], search))
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
      <p className="csp-s-0287">
        {list ? "Altere o nome da lista e os produtos associados." : "Digite um nome e escolha os produtos da nova lista."}
      </p>
      <form onSubmit={handleSubmit}>
        <TextInput label="Nome *" value={name} onChange={(e) => setName(e.target.value)} required />

        {(
          <div className="csp-s-0288">
            <span
              className="csp-s-0289"
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
              className="csp-s-0290"
            >
              {filteredProducts.length === 0 ? (
                <span className="csp-s-0291">Nenhum produto encontrado.</span>
              ) : (
                filteredProducts.map((p) => (
                  <label key={p.id} className="csp-s-0292">
                    <input type="checkbox" checked={selectedIds.has(p.id)} onChange={() => toggleProduct(p.id)} />
                    <span className="csp-s-0293">{p.name}</span>
                  </label>
                ))
              )}
            </div>
          </div>
        )}

        <p style={{ color: "var(--text-muted)", font: "var(--text-role-body)" }}>Rascunho salvo neste navegador até você salvar a lista.</p>
        <div className="csp-s-0294">
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
      <p className="csp-s-0295">
        Tem certeza que deseja remover esta lista? Esta ação não pode ser desfeita.
      </p>
      <div className="csp-s-0296">
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

