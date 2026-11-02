import { useMemo, useState, useCallback, type ReactNode } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { catalogApi, CATALOG_SORT_OPTIONS, type CatalogProduct, type CatalogSortType } from "../../api/catalog"
import { productsApi } from "../../api/products"
import { useAuthStore } from "../../stores/authStore"
import { formDraftKey } from "../../lib/formDraftStorage"
import { useAutosavedDraft } from "../../hooks/useAutosavedDraft"
import { Panel } from "../ui/Panel"
import { Button } from "../ui/Button"
import { IconButton } from "../ui/IconButton"
import { SearchField } from "../ui/SearchField"
import { Select } from "../ui/Select"
import { Badge } from "../ui/Badge"
import { Icon } from "../ui/Icon"
import { Modal } from "../ui/Modal"
import { formatEarnings, formatPriceRange, formatRate, round2, toNumber } from "../../lib/commission"

// A API da Shopee não tem paginação nativa (só `limit`, ver
// api/shopee_catalog.py) — busca 1 vez com limite alto e pagina os
// resultados no cliente, em blocos deste tamanho.
const CLIENT_PAGE_SIZE = 50
const SEARCH_LIMIT = 150

function formatCatalogPrice(product: CatalogProduct): string {
  return formatPriceRange(product.price_min, product.price_max)
}

/** Ganho por venda: preço × taxa; sem preço, usa o valor que a Shopee devolveu. */
function formatCatalogEarnings(product: CatalogProduct): string {
  const fromRate = formatEarnings(product.price_min, product.price_max, product.commission)
  if (fromRate !== "—") return fromRate
  return product.commission_amount != null ? formatPriceRange(product.commission_amount, null) : "—"
}

function toPrice(value: string | null): number | null {
  const n = toNumber(value)
  return n == null ? null : round2(n)
}

interface CatalogCardProps {
  product: CatalogProduct
  added: boolean
  onOpen: () => void
}

function CatalogThumb({ image, size }: { image: string | null; size: number }) {
  const box = { width: size, height: size, borderRadius: "var(--r-md)", background: "var(--surface-inset)", flexShrink: 0 } as const
  return image ? (
    <img src={image} alt="" style={{ ...box, objectFit: "cover" }} />
  ) : (
    <span style={{ ...box, display: "inline-flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)" }}>
      <Icon name="package" size={Math.round(size * 0.4)} />
    </span>
  )
}

function CatalogBadges({ product }: { product: CatalogProduct }) {
  return (
    <div className="csp-s-0042">
      <Badge tone="outline">{formatCatalogPrice(product)}</Badge>
      {product.commission != null ? <Badge tone="outline">Comissão {formatRate(product.commission)}</Badge> : null}
      {product.commission != null || product.commission_amount != null ? (
        <Badge tone="outline">Ganho {formatCatalogEarnings(product)}/venda</Badge>
      ) : null}
      {product.sales != null ? <Badge tone="outline">{product.sales} vendas</Badge> : null}
      {product.rating_star != null ? <Badge tone="outline">★ {product.rating_star}</Badge> : null}
    </div>
  )
}

function CatalogCard({ product, added, onOpen }: CatalogCardProps) {
  return (
    <Panel
      surface="dark"
      role="button"
      tabIndex={0}
      aria-label={`Ver detalhes de ${product.name}`}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault()
          onOpen()
        }
      }}
      style={{ padding: 14, display: "flex", flexDirection: "column", gap: 10, cursor: "pointer" }}
    >
      <div className="csp-s-0043">
        <CatalogThumb image={product.image} size={64} />
        <div className="csp-s-0044">
          <p
            title={product.name}
            className="csp-s-0045"
          >
            {product.name}
          </p>
          {product.shop_name ? (
            <p className="csp-s-0046">{product.shop_name}</p>
          ) : null}
        </div>
      </div>
      <CatalogBadges product={product} />
      {added ? <Badge tone="mint">Adicionado aos meus produtos</Badge> : null}
    </Panel>
  )
}

interface CatalogDetailsModalProps {
  product: CatalogProduct | null
  added: boolean
  isAdding: boolean
  error: string | null
  onClose: () => void
  onConfirm: (p: CatalogProduct) => void
  onEdit: (p: CatalogProduct) => void
}

function DetailRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="csp-s-0047">
      <span className="csp-s-0048">
        {label}
      </span>
      <span className="csp-s-0049">{children}</span>
    </div>
  )
}

function CatalogDetailsModal({ product, added, isAdding, error, onClose, onConfirm, onEdit }: CatalogDetailsModalProps) {
    return (
    <Modal open={product != null} onClose={onClose} title="Detalhes do produto" width={520}>
      {product ? (
        <div className="csp-s-0050">
          <div className="csp-s-0051">
            <CatalogThumb image={product.image} size={96} />
            <div className="csp-s-0052">
              <p className="csp-s-0053">{product.name}</p>
              {product.shop_name ? (
                <p className="csp-s-0054">{product.shop_name}</p>
              ) : null}
            </div>
          </div>
          <CatalogBadges product={product} />
          <div className="csp-s-0055">
            <DetailRow label="ID Shopee">{product.product_id}</DetailRow>
            <DetailRow label="Preço">{formatCatalogPrice(product)}</DetailRow>
            <DetailRow label="Taxa de comissão">{formatRate(product.commission)}</DetailRow>
            <DetailRow label="Ganho estimado por venda">{formatCatalogEarnings(product)}</DetailRow>
          </div>
          {product.original_link || product.commission_link ? (
            <div className="csp-s-0056">
              {product.original_link ? (
                <a href={product.original_link} target="_blank" rel="noreferrer" className="csp-named-link">Link original ↗</a>
              ) : null}
              {product.commission_link ? (
                <a href={product.commission_link} target="_blank" rel="noreferrer" className="csp-named-link">Link de comissão ↗</a>
              ) : null}
            </div>
          ) : null}
          {error ? <div role="alert" className="csp-s-0057">{error}</div> : null}
          <div className="csp-s-0058">
            <Button type="button" variant="ghost" onClick={() => onEdit(product)} disabled={added || isAdding}>
              Editar antes de salvar
            </Button>
            <Button
              type="button"
              variant="primary"
              icon={added ? "check" : "plus"}
              loading={isAdding}
              disabled={added}
              onClick={() => onConfirm(product)}
            >
              {added ? "Adicionado" : isAdding ? "Adicionando..." : "Adicionar aos meus produtos"}
            </Button>
          </div>
        </div>
      ) : null}
    </Modal>
  )
}

interface CatalogSearchTabProps {
  /** Abre o formulario de cadastro manual (em branco). */
  onManualCreate: () => void
  /** Abre o formulario ja preenchido com os dados do catalogo. */
  onPrefill: (product: CatalogProduct) => void
}

export function CatalogSearchTab({ onManualCreate, onPrefill }: CatalogSearchTabProps) {
  const queryClient = useQueryClient()
  const accountId = useAuthStore((state) => state.user?.id)
  const [keywordInput, setKeywordInput] = useState("")
  const [searchKeyword, setSearchKeyword] = useState<string | undefined>(undefined)
  const [sortType, setSortType] = useState<CatalogSortType>(1)
  const [categoryId, setCategoryId] = useState<string>("")
  const [page, setPage] = useState(1)
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set())
  const [hasSearched, setHasSearched] = useState(false)
  const [selected, setSelected] = useState<CatalogProduct | null>(null)

  useAutosavedDraft(formDraftKey(accountId, "catalog-search", null, false),
    { keywordInput, searchKeyword, sortType, categoryId, page, hasSearched },
    (saved) => {
      setKeywordInput(typeof saved?.keywordInput === "string" ? saved.keywordInput : "")
      setSearchKeyword(typeof saved?.searchKeyword === "string" ? saved.searchKeyword : undefined)
      setSortType(saved?.sortType && [1, 2, 3, 4, 5].includes(saved.sortType) ? saved.sortType : 1)
      setCategoryId(typeof saved?.categoryId === "string" ? saved.categoryId : "")
      setPage(typeof saved?.page === "number" && saved.page > 0 ? Math.floor(saved.page) : 1)
      setHasSearched(saved?.hasSearched === true)
    },
  )

  const categoriesQuery = useQuery({
    queryKey: ["catalog-categories"],
    queryFn: () => catalogApi.categories(),
    staleTime: 30 * 60 * 1000,
  })

  const searchQuery = useQuery({
    queryKey: ["catalog-search", searchKeyword, categoryId, sortType],
    queryFn: () =>
      catalogApi.search({
        keyword: searchKeyword,
        product_cat_id: categoryId ? Number(categoryId) : undefined,
        sort_type: sortType,
        limit: SEARCH_LIMIT,
      }),
    enabled: hasSearched,
  })

  const addMutation = useMutation({
    mutationFn: (product: CatalogProduct) =>
      productsApi.create({
        product_id: product.product_id,
        name: product.name,
        original_link: product.original_link ?? '',
        commission_link: product.commission_link ?? '',
        commission: product.commission != null ? round2(product.commission) : null,
        image: product.image,
        price_min: toPrice(product.price_min),
        price_max: toPrice(product.price_max),
      }),
    meta: { toast: { pending: "Salvando produto…", success: "Produto adicionado a Meus Produtos", error: "Não foi possível adicionar" } },
    onSuccess: (_data, product) => {
      setAddedIds((prev) => new Set(prev).add(product.product_id))
      queryClient.invalidateQueries({ queryKey: ["products"] })
      setSelected(null)
    },
  })

  const handleSearch = useCallback(() => {
    setSearchKeyword(keywordInput.trim() || undefined)
    setPage(1)
    setHasSearched(true)
  }, [keywordInput])

  const results = searchQuery.data?.data ?? []
  const totalPages = Math.max(1, Math.ceil(results.length / CLIENT_PAGE_SIZE))
  const pageItems = useMemo(
    () => results.slice((page - 1) * CLIENT_PAGE_SIZE, page * CLIENT_PAGE_SIZE),
    [results, page],
  )

  const categoryOptions = [
    { value: "", label: "Todas as categorias" },
    ...(categoriesQuery.data?.data ?? []).map((c) => ({ value: String(c.category_id), label: c.name })),
  ]

  return (
    <div className="csp-s-0059">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          handleSearch()
        }}
        className="catalog-search-filters"
        style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "flex-end" }}
      >
        <SearchField
          value={keywordInput}
          onChange={(e) => setKeywordInput(e.target.value)}
          placeholder="Buscar no catálogo da Shopee..."
          width={280}
        />
        <Select
          label="Ordenar por"
          value={String(sortType)}
          onChange={(e) => setSortType(Number(e.target.value) as CatalogSortType)}
          options={CATALOG_SORT_OPTIONS.map((o) => ({ value: String(o.value), label: o.label }))}
          width={220}
        />
        <Select
          label="Categoria"
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
          options={categoryOptions}
          disabled={categoriesQuery.isLoading}
          width={220}
        />
        <Button type="submit" variant="primary" icon="search" disabled={searchQuery.isFetching}>
          {searchQuery.isFetching ? "Buscando..." : "Buscar"}
        </Button>
        <Button type="button" variant="ghost" icon="plus" onClick={onManualCreate}>
          Cadastrar manualmente
        </Button>
      </form>

      {searchQuery.isError ? (
        <div
          className="csp-s-0060"
        >
          {searchQuery.error instanceof Error ? searchQuery.error.message : "Erro ao buscar produtos."}
        </div>
      ) : null}

      {!hasSearched ? (
        <Panel surface="dark" style={{ padding: "48px 16px", textAlign: "center" }}>
          <p className="csp-s-0061">
            Busque produtos no catálogo real da Shopee usando sua credencial de afiliado.
          </p>
        </Panel>
      ) : searchQuery.isLoading ? (
        <div className="csp-s-0062">
          Buscando...
        </div>
      ) : results.length === 0 ? (
        <Panel surface="dark" style={{ padding: "48px 16px", textAlign: "center" }}>
          <p className="csp-s-0063">
            Nenhum produto encontrado para essa busca.
          </p>
        </Panel>
      ) : (
        <>
          <div
            className="csp-s-0064"
          >
            {pageItems.map((product) => (
              <CatalogCard
                key={product.product_id}
                product={product}
                added={addedIds.has(product.product_id)}
                onOpen={() => {
                  addMutation.reset()
                  setSelected(product)
                }}
              />
            ))}
          </div>

          {totalPages > 1 ? (
            <div className="csp-s-0065">
              <IconButton
                icon="chevron-left"
                label="Página anterior"
                tone="plain"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                style={{ opacity: page === 1 ? 0.4 : 1, cursor: page === 1 ? "not-allowed" : "pointer" }}
              />
              <span className="csp-s-0066">
                Página {page} de {totalPages}
              </span>
              <IconButton
                icon="chevron-right"
                label="Próxima página"
                tone="plain"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                style={{ opacity: page === totalPages ? 0.4 : 1, cursor: page === totalPages ? "not-allowed" : "pointer" }}
              />
            </div>
          ) : null}
        </>
      )}
      <CatalogDetailsModal
        product={selected}
        added={selected != null && addedIds.has(selected.product_id)}
        isAdding={addMutation.isPending}
        error={addMutation.isError ? (addMutation.error instanceof Error ? addMutation.error.message : "Erro ao adicionar produto.") : null}
        onClose={() => setSelected(null)}
        onConfirm={(p) => addMutation.mutate(p)}
        onEdit={(p) => {
          setSelected(null)
          onPrefill(p)
        }}
      />
    </div>
  )
}
