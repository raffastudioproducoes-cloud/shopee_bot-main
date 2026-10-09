import { useMemo, useState, useCallback, type ReactNode } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { catalogApi, CATALOG_SORT_OPTIONS, type CatalogProduct, type CatalogSortType } from "../../api/catalog"
import { productsApi } from "../../api/products"
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
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
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
      <div style={{ display: "flex", gap: 12 }}>
        <CatalogThumb image={product.image} size={64} />
        <div style={{ minWidth: 0, flex: 1 }}>
          <p
            title={product.name}
            style={{
              margin: 0,
              font: "var(--text-role-body)",
              color: "var(--text-body)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
            }}
          >
            {product.name}
          </p>
          {product.shop_name ? (
            <p style={{ margin: "4px 0 0", font: "var(--text-role-label)", color: "var(--text-muted)" }}>{product.shop_name}</p>
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
    <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0 }}>
      <span style={{ font: "var(--text-role-label)", letterSpacing: "var(--ls-label)", textTransform: "uppercase", color: "var(--text-muted)" }}>
        {label}
      </span>
      <span style={{ font: "var(--text-role-body)", color: "var(--text-body)", overflowWrap: "anywhere" }}>{children}</span>
    </div>
  )
}

function CatalogDetailsModal({ product, added, isAdding, error, onClose, onConfirm, onEdit }: CatalogDetailsModalProps) {
  const linkStyle = { color: "var(--sky-300)" } as const
  return (
    <Modal open={product != null} onClose={onClose} title="Detalhes do produto" width={520}>
      {product ? (
        <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", gap: 14 }}>
            <CatalogThumb image={product.image} size={96} />
            <div style={{ minWidth: 0, flex: 1 }}>
              <p style={{ margin: 0, font: "var(--text-role-title)", color: "var(--text-display)", overflowWrap: "anywhere" }}>{product.name}</p>
              {product.shop_name ? (
                <p style={{ margin: "4px 0 0", font: "var(--text-role-label)", color: "var(--text-muted)" }}>{product.shop_name}</p>
              ) : null}
            </div>
          </div>
          <CatalogBadges product={product} />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
            <DetailRow label="ID Shopee">{product.product_id}</DetailRow>
            <DetailRow label="Preço">{formatCatalogPrice(product)}</DetailRow>
            <DetailRow label="Taxa de comissão">{formatRate(product.commission)}</DetailRow>
            <DetailRow label="Ganho estimado por venda">{formatCatalogEarnings(product)}</DetailRow>
          </div>
          {product.original_link || product.commission_link ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {product.original_link ? (
                <a href={product.original_link} target="_blank" rel="noreferrer" style={linkStyle}>Link original ↗</a>
              ) : null}
              {product.commission_link ? (
                <a href={product.commission_link} target="_blank" rel="noreferrer" style={linkStyle}>Link de comissão ↗</a>
              ) : null}
            </div>
          ) : null}
          {error ? <div role="alert" style={{ color: "var(--negative)", font: "var(--text-role-body)" }}>{error}</div> : null}
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "flex-end", gap: 12 }}>
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
  const [keywordInput, setKeywordInput] = useState("")
  const [searchKeyword, setSearchKeyword] = useState<string | undefined>(undefined)
  const [sortType, setSortType] = useState<CatalogSortType>(1)
  const [categoryId, setCategoryId] = useState<string>("")
  const [page, setPage] = useState(1)
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set())
  const [hasSearched, setHasSearched] = useState(false)
  const [selected, setSelected] = useState<CatalogProduct | null>(null)

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
        original_link: product.original_link,
        commission_link: product.commission_link,
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
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          handleSearch()
        }}
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
          style={{
            padding: "12px 16px",
            borderRadius: "var(--r-md)",
            border: "1px solid var(--negative)",
            color: "var(--negative)",
            font: "var(--text-role-body)",
          }}
        >
          {searchQuery.error instanceof Error ? searchQuery.error.message : "Erro ao buscar produtos."}
        </div>
      ) : null}

      {!hasSearched ? (
        <Panel surface="dark" style={{ padding: "48px 16px", textAlign: "center" }}>
          <p style={{ color: "var(--text-muted)", font: "var(--text-role-body)", margin: 0 }}>
            Busque produtos no catálogo real da Shopee usando sua credencial de afiliado.
          </p>
        </Panel>
      ) : searchQuery.isLoading ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 200, color: "var(--text-muted)" }}>
          Buscando...
        </div>
      ) : results.length === 0 ? (
        <Panel surface="dark" style={{ padding: "48px 16px", textAlign: "center" }}>
          <p style={{ color: "var(--text-muted)", font: "var(--text-role-body)", margin: 0 }}>
            Nenhum produto encontrado para essa busca.
          </p>
        </Panel>
      ) : (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
              gap: 12,
              alignItems: "start",
            }}
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
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12 }}>
              <IconButton
                icon="chevron-left"
                label="Página anterior"
                tone="plain"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                style={{ opacity: page === 1 ? 0.4 : 1, cursor: page === 1 ? "not-allowed" : "pointer" }}
              />
              <span style={{ color: "var(--text-muted)", font: "var(--text-role-body)" }}>
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
