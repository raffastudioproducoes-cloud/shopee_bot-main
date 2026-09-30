import { useMemo, useState, useCallback } from "react"
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

// A API da Shopee não tem paginação nativa (só `limit`, ver
// api/shopee_catalog.py) — busca 1 vez com limite alto e pagina os
// resultados no cliente, em blocos deste tamanho.
const CLIENT_PAGE_SIZE = 50
const SEARCH_LIMIT = 150

function toNullableNumber(value: string | null): number | null {
  if (value == null || value === "") return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

function formatCatalogPrice(product: CatalogProduct): string {
  const min = toNullableNumber(product.price_min)
  const max = toNullableNumber(product.price_max)
  if (min != null && max != null) return `R$ ${min.toFixed(2)} – R$ ${max.toFixed(2)}`
  if (min != null) return `R$ ${min.toFixed(2)}+`
  return "—"
}

interface CatalogCardProps {
  product: CatalogProduct
  added: boolean
  onAdd: () => void
  isAdding: boolean
}

function CatalogCard({ product, added, onAdd, isAdding }: CatalogCardProps) {
  return (
    <Panel surface="dark" style={{ padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", gap: 12 }}>
        {product.image ? (
          <img
            src={product.image}
            alt=""
            style={{ width: 64, height: 64, borderRadius: "var(--r-md)", objectFit: "cover", background: "var(--surface-inset)", flexShrink: 0 }}
          />
        ) : (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 64,
              height: 64,
              borderRadius: "var(--r-md)",
              background: "var(--surface-inset)",
              color: "var(--text-muted)",
              flexShrink: 0,
            }}
          >
            <Icon name="package" size={24} />
          </span>
        )}
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
            <p style={{ margin: "4px 0 0", font: "var(--text-role-label)", color: "var(--text-muted)" }}>
              {product.shop_name}
            </p>
          ) : null}
        </div>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        <Badge tone="outline">{formatCatalogPrice(product)}</Badge>
        {product.commission != null ? <Badge tone="outline">Comissão {product.commission}%</Badge> : null}
        {product.commission_rate != null ? <Badge tone="outline">Taxa {product.commission_rate}</Badge> : null}
        {product.sales != null ? <Badge tone="outline">{product.sales} vendas</Badge> : null}
        {product.rating_star != null ? <Badge tone="outline">★ {product.rating_star}</Badge> : null}
      </div>

      <Button
        variant={added ? "secondary" : "primary"}
        icon={added ? "check" : "plus"}
        disabled={added || isAdding}
        onClick={onAdd}
        size="sm"
        fullWidth
      >
        {added ? "Adicionado" : isAdding ? "Adicionando..." : "Adicionar aos meus produtos"}
      </Button>
    </Panel>
  )
}

export function CatalogSearchTab() {
  const queryClient = useQueryClient()
  const [keywordInput, setKeywordInput] = useState("")
  const [searchKeyword, setSearchKeyword] = useState<string | undefined>(undefined)
  const [sortType, setSortType] = useState<CatalogSortType>(1)
  const [categoryId, setCategoryId] = useState<string>("")
  const [page, setPage] = useState(1)
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set())
  const [hasSearched, setHasSearched] = useState(false)

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
        commission: toNullableNumber(product.commission),
        image: product.image,
        price_min: toNullableNumber(product.price_min),
        price_max: toNullableNumber(product.price_max),
      }),
    onSuccess: (_data, product) => {
      setAddedIds((prev) => new Set(prev).add(product.product_id))
      queryClient.invalidateQueries({ queryKey: ["products"] })
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

      {addMutation.isError ? (
        <div
          style={{
            padding: "12px 16px",
            borderRadius: "var(--r-md)",
            border: "1px solid var(--negative)",
            color: "var(--negative)",
            font: "var(--text-role-body)",
          }}
        >
          {addMutation.error instanceof Error ? addMutation.error.message : "Erro ao adicionar produto."}
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
                isAdding={addMutation.isPending && addMutation.variables?.product_id === product.product_id}
                onAdd={() => addMutation.mutate(product)}
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
    </div>
  )
}
