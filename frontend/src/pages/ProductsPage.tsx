import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, useCallback } from "react"
import { useAuthStore } from "../stores/authStore"
import { formDraftKey, clearFormDraft, saveFormDraft } from "../lib/formDraftStorage"
import { useAutosavedDraft } from "../hooks/useAutosavedDraft"
import { router } from "../router"
import { productsApi, type Product } from "../api/products"
import { PlanSummary } from "../components/plans/PlanSummary"
import { usePlanUsage } from "../hooks/usePlanUsage"
import { resourceAtLimit } from "../lib/planPresentation"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { PageSkeleton } from "../components/ui/Skeleton"
import { IconButton } from "../components/ui/IconButton"
import { TextInput } from "../components/ui/TextInput"
import { Modal } from "../components/ui/Modal"
import { SearchField } from "../components/ui/SearchField"
import { SegmentedToggle } from "../components/ui/SegmentedToggle"
import { ViewSwitcher, useViewMode, viewContainerStyle } from "../components/ui/ViewSwitcher"
import { TimelineListCard } from "../components/ui/TimelineListCard"
import { Badge } from "../components/ui/Badge"
import { Icon } from "../components/ui/Icon"
import { CatalogSearchTab } from "../components/products/CatalogSearchTab"
import type { CatalogProduct } from "../api/catalog"
import { formatEarnings, formatPriceRange as formatRange, formatRate, round2, toNumber } from "../lib/commission"

type ProductsTab = "mine" | "catalog"

const TABS_OPTIONS = [
  { value: "mine", label: "Meus Produtos" },
  { value: "catalog", label: "Pesquisa Avançada" },
]

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

function formatPriceRange(product: Product): string {
  return formatRange(product.price_min, product.price_max)
}

/** Texto do input number com no máx. 2 casas (evita o aviso do navegador com step=0.01). */
function toFormNumber(value: number | string | null | undefined): string {
  const n = toNumber(value)
  return n == null ? "" : String(round2(n))
}

const formNumber = (value: string) => (value ? round2(Number(value)) : null)

export function ProductsPage() {
  const { isAuthenticated, logout, user } = useAuthStore()
  const queryClient = useQueryClient()
  const planQuery = usePlanUsage()
  const productsAtLimit = !planQuery.isError && resourceAtLimit(planQuery.data?.resources.products)
  const [activeTab, setActiveTab] = useState<ProductsTab>("mine")
  const [search, setSearch] = useState("")
  useAutosavedDraft(formDraftKey(user?.id, "products-filters", null, false), { activeTab, search }, (saved) => {
    setActiveTab(saved?.activeTab === "catalog" ? "catalog" : "mine")
    setSearch(typeof saved?.search === "string" ? saved.search : "")
  })
  const [view, handleViewChange] = useViewMode("products-view")
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [formBase, setFormBase] = useState(emptyForm)
  const [deleteId, setDeleteId] = useState<number | null>(null)
  const activeDraftKey = modalOpen
    ? formDraftKey(user?.id, editingId ? `product-edit:${editingId}` : "product-create", null, false)
    : null
  useAutosavedDraft(activeDraftKey, form, (saved) => {
    const base = saved && typeof saved === "object" ? saved : formBase
    setForm({
      name: typeof base.name === "string" ? base.name : "",
      product_id: typeof base.product_id === "string" ? base.product_id : "",
      original_link: typeof base.original_link === "string" ? base.original_link : "",
      commission_link: typeof base.commission_link === "string" ? base.commission_link : "",
      commission: typeof base.commission === "string" ? base.commission : "",
      image: typeof base.image === "string" ? base.image : "",
      price_min: typeof base.price_min === "string" ? base.price_min : "",
      price_max: typeof base.price_max === "string" ? base.price_max : "",
    })
  })

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
      productsApi.create({
        ...body,
        original_link: body.original_link ?? '',
        commission_link: body.commission_link ?? '',
      }),
    meta: { toast: { pending: "Salvando produto…", success: "Produto adicionado a Meus Produtos", error: "Não foi possível salvar" } },
    onSuccess: () => {
      clearFormDraft(formDraftKey(user?.id, "product-create", null, false))
      queryClient.invalidateQueries({ queryKey: ["products"] })
      queryClient.invalidateQueries({ queryKey: ["plan-usage"] })
      setModalOpen(false)
      setForm(emptyForm)
    },
    onError: onAuthError,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<Product> }) =>
      productsApi.update(id, body),
    meta: { toast: { pending: "Salvando alterações…", success: "Produto atualizado", error: "Não foi possível salvar" } },
    onSuccess: (_result, variables) => {
      clearFormDraft(formDraftKey(user?.id, `product-edit:${variables.id}`, null, false))
      queryClient.invalidateQueries({ queryKey: ["products"] })
      queryClient.invalidateQueries({ queryKey: ["plan-usage"] })
      setEditingId(null)
      setModalOpen(false)
      setForm(emptyForm)
    },
    onError: onAuthError,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => productsApi.delete(id),
    meta: { toast: { pending: "Removendo produto…", success: "Produto removido", error: "Não foi possível remover" } },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] })
      queryClient.invalidateQueries({ queryKey: ["plan-usage"] })
      setDeleteId(null)
    },
    onError: onAuthError,
  })

  // ── Handlers ───────────────────────────────────────────────────────────────────

  const handleCreate = useCallback(() => {
      if (productsAtLimit) return
      createMutation.mutate({
        name: form.name,
        product_id: form.product_id,
        original_link: form.original_link,
        commission_link: form.commission_link,
        commission: formNumber(form.commission),
        image: form.image || null,
        price_min: formNumber(form.price_min),
        price_max: formNumber(form.price_max),
        category: null,
      })
    }, [form, createMutation, productsAtLimit])

  const handleUpdate = useCallback(() => {
    if (!editingId) return
    updateMutation.mutate({
      id: editingId,
      body: {
        name: form.name,
        product_id: form.product_id,
        original_link: form.original_link,
        commission_link: form.commission_link,
        commission: formNumber(form.commission),
        image: form.image || null,
        price_min: formNumber(form.price_min),
        price_max: formNumber(form.price_max),
      },
    })
  }, [form, editingId, updateMutation])

  const handleDelete = useCallback(() => {
    if (deleteId) deleteMutation.mutate(deleteId)
  }, [deleteId, deleteMutation])

  const handleEdit = useCallback((product: Product) => {
    setEditingId(product.id)
    const nextForm = {
      name: product.name || "",
      product_id: product.product_id || "",
      original_link: product.original_link || "",
      commission_link: product.commission_link || "",
      commission: toFormNumber(product.commission),
      image: product.image || "",
      price_min: toFormNumber(product.price_min),
      price_max: toFormNumber(product.price_max),
    }
    setFormBase(nextForm)
    setForm(nextForm)
    setModalOpen(true)
  }, [])

  const handlePrefill = useCallback((p: CatalogProduct) => {
    if (productsAtLimit) return
    setEditingId(null)
    const nextForm = {
      name: p.name,
      product_id: p.product_id,
      original_link: p.original_link || "",
      commission_link: p.commission_link || "",
      commission: toFormNumber(p.commission),
      image: p.image || "",
      price_min: toFormNumber(p.price_min),
      price_max: toFormNumber(p.price_max),
    }
    setFormBase(nextForm)
    setForm(nextForm)
    saveFormDraft(formDraftKey(user?.id, "product-create", null, false), nextForm)
    setModalOpen(true)
  }, [user?.id, productsAtLimit])

  const handleCancel = useCallback(() => {
    setModalOpen(false)
    setEditingId(null)
    setForm(emptyForm)
  }, [])

  const openCreateModal = useCallback(() => {
    if (productsAtLimit) return
    setEditingId(null)
    setFormBase(emptyForm)
    setForm(emptyForm)
    setModalOpen(true)
  }, [productsAtLimit])

  // ── Render ────────────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <PageSkeleton variant="table" titleWidth="180px" subtitleWidth="260px" action toolbar />
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="csp-s-0350">
        <p className="csp-s-0351">Não autenticado.</p>
        <Button variant="primary" onClick={() => router.navigate({ to: "/login" })} style={{ marginTop: 16 }}>
          Ir para login
        </Button>
      </div>
    )
  }

  return (
    <div className="csp-s-0352">
      {/* Header */}
      <header className="products-page-header" style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        <div>
          <h1 className="csp-s-0353">Produtos</h1>
          <p className="csp-s-0354">Catálogo de produtos da Shopee.</p>
          <div className="csp-s-0355">
            <SegmentedToggle
              options={TABS_OPTIONS}
              value={activeTab}
              onChange={(v) => setActiveTab(v as ProductsTab)}
              fullWidth={false}
              size={36}
            />
            {activeTab === "mine" ? (
              <ViewSwitcher value={view} onChange={handleViewChange} />
            ) : null}
          </div>
        </div>
        {activeTab === "mine" ? (
          <div className="csp-s-0356">
            <SearchField
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar produtos..."
              width={240}
            />
          </div>
        ) : null}
      </header>

      <PlanSummary resources={["products"]} />
      {activeTab === "catalog" ? (
        <CatalogSearchTab createBlocked={productsAtLimit} onManualCreate={openCreateModal} onPrefill={handlePrefill} />
      ) : (
        <>
      {/* Error */}
      {error && (
        <div
          className="csp-s-0357"
        >
          {error.message}
        </div>
      )}

      {/* Products */}
      {products.length === 0 ? (
        <Panel surface="dark" style={{ padding: "48px 16px", textAlign: "center" }}>
          <p className="csp-s-0358">Nenhum produto cadastrado.</p>
          <Button variant="primary" icon="search" style={{ marginTop: 16 }} onClick={() => setActiveTab("catalog")}>
            Buscar na Pesquisa Avançada
          </Button>
        </Panel>
      ) : (
        <div style={viewContainerStyle(view)}>
          {products.map((product: Product) => (
            <TimelineListCard
              key={product.id}
              title={product.name}
              subtitle={product.product_id}
              thumbnail={
                product.image ? (
                  <img
                    src={product.image}
                    alt=""
                    className="csp-s-0359"
                  />
                ) : (
                  <span
                    className="csp-s-0360"
                  >
                    <Icon name="package" size={18} />
                  </span>
                )
              }
              badge={product.category ? <Badge tone="outline">{product.category}</Badge> : undefined}
              actions={
                <>
                  <IconButton icon="pencil" label="Editar" tone="plain" size={30} onClick={() => handleEdit(product)} />
                  <IconButton icon="trash-2" label="Remover" tone="plain" size={30} onClick={() => setDeleteId(product.id)} />
                </>
              }
              stats={[
                { icon: "hash", label: "ID Shopee", value: product.product_id },
                { icon: "dollar-sign", label: "Preço", value: formatPriceRange(product) },
                { icon: "percent", label: "Comissão", value: formatRate(product.commission) },
                { icon: "dollar-sign", label: "Ganho/venda", value: formatEarnings(product.price_min, product.price_max, product.commission) },
                { icon: "calendar", label: "Cadastrado", value: new Date(product.created_at).toLocaleDateString("pt-BR") },
              ]}
              sections={[
                { label: "Produto", category: product.category || undefined, content: product.name },
                { label: "Preço", category: "Faixa", content: formatPriceRange(product) },
                {
                  label: "Comissão",
                  category: "Taxa e ganho",
                  content: `${formatRate(product.commission)} · ganho estimado ${formatEarnings(product.price_min, product.price_max, product.commission)} por venda`,
                },
                {
                  label: "Links",
                  category: "Afiliado",
                  content: (
                    <div className="csp-s-0361">
                      {product.original_link ? (
                        <a href={product.original_link} target="_blank" rel="noreferrer" className="csp-s-0362">
                          {product.original_link}
                        </a>
                      ) : null}
                      {product.commission_link ? (
                        <a href={product.commission_link} target="_blank" rel="noreferrer" className="csp-s-0363">
                          {product.commission_link}
                        </a>
                      ) : null}
                      {!product.original_link && !product.commission_link ? "—" : null}
                    </div>
                  ),
                },
                {
                  label: "Cadastro",
                  category: "Datas",
                  content: (
                    <div className="csp-s-0364">
                      <span>Criado em {new Date(product.created_at).toLocaleString("pt-BR")}</span>
                      {product.updated_at ? <span className="csp-s-0365">Atualizado em {new Date(product.updated_at).toLocaleString("pt-BR")}</span> : null}
                    </div>
                  ),
                },
              ]}
            />
          ))}
        </div>
      )}
        </>
      )}

      {/* Modal de criação/edição */}
      <Modal open={modalOpen} onClose={handleCancel} title={editingId ? "Editar produto" : "Novo produto"} width={560}>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            editingId ? handleUpdate() : handleCreate()
          }}
          className="csp-s-0366"
        >
          <div className="mobile-form-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <TextInput
              label="Nome *"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              required
            />
            <TextInput
              label="ID Shopee *"
              inputMode="numeric"
              pattern="[0-9]+"
              title="Somente números (ID do item na Shopee)"
              value={form.product_id}
              onChange={(e) => setForm((f) => ({ ...f, product_id: e.target.value }))}
              required
              inputStyle={{ fontFamily: "monospace" }}
            />
          </div>

          <TextInput
            label="Link original *"
            type="url"
            required
            value={form.original_link}
            onChange={(e) => setForm((f) => ({ ...f, original_link: e.target.value }))}
            placeholder="https://..."
          />

          <TextInput
            label="Link de comissão *"
            type="url"
            required
            value={form.commission_link}
            onChange={(e) => setForm((f) => ({ ...f, commission_link: e.target.value }))}
            placeholder="https://..."
          />

          <div className="mobile-form-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <TextInput
              label="Taxa de comissão (%)"
              type="number"
              step="0.01"
              min="0"
              max="100"
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

          <div className="mobile-form-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
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

          <p aria-live="polite" className="csp-s-0367">
            Ganho estimado por venda: <strong className="csp-s-0368">{formatEarnings(form.price_min, form.price_max, form.commission)}</strong>
          </p>

          <p style={{ color: "var(--text-muted)", font: "var(--text-role-caption)" }}>Rascunho salvo neste navegador até você salvar o produto.</p>
          <div className="csp-s-0369">
            <Button type="button" variant="ghost" onClick={handleCancel}>
              Cancelar
            </Button>
            <Button type="submit" variant="primary" disabled={!editingId && productsAtLimit} loading={createMutation.isPending || updateMutation.isPending}>
              {createMutation.isPending || updateMutation.isPending ? "Salvando..." : editingId ? "Salvar" : "Criar"}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal de exclusão */}
      <Modal open={deleteId != null} onClose={() => setDeleteId(null)} title="Confirmar remoção" width={400}>
        <p className="csp-s-0370">
          Tem certeza que deseja remover este produto? Esta ação não pode ser desfeita.
        </p>
        <div className="csp-s-0371">
          <Button variant="ghost" onClick={() => setDeleteId(null)}>
            Cancelar
          </Button>
          <Button variant="send" onClick={handleDelete} loading={deleteMutation.isPending}>
            {deleteMutation.isPending ? "Removendo..." : "Remover"}
          </Button>
        </div>
      </Modal>
    </div>
  )
}
