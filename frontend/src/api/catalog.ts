import { api } from '../lib/api'

/** Um resultado bruto de busca no catálogo real da Shopee (Affiliate Open
 * API) — NÃO é um `Product` da tabela `products` (ver api/products.ts).
 * Campos best-effort (sales/rating_star/shop_name/commission_rate) podem
 * vir `null` quando a Shopee não aceitou esses campos extra na consulta
 * (ver fallback de schema em api/shopee_catalog.py) — sempre renderizar
 * condicionalmente, nunca assumir presença. */
export interface CatalogProduct {
  product_id: string
  name: string
  original_link: string | null
  commission_link: string | null
  commission: string | null
  image: string | null
  price_min: string | null
  price_max: string | null
  sales: number | null
  rating_star: number | null
  shop_name: string | null
  commission_rate: string | null
}

export interface CatalogSearchResponse {
  data: CatalogProduct[]
}

export interface CatalogCategory {
  name: string
  category_id: number
  parent_id: number | null
}

export interface CatalogCategoriesResponse {
  data: CatalogCategory[]
}

/** sortType da Shopee Affiliate Open API — sem opção de "mais recentes",
 * a API não oferece esse critério (ver api/shopee_catalog.py). */
export type CatalogSortType = 1 | 2 | 3 | 4 | 5

export const CATALOG_SORT_OPTIONS: { value: CatalogSortType; label: string }[] = [
  { value: 1, label: "Relevância" },
  { value: 2, label: "Mais vendidos" },
  { value: 3, label: "Preço: maior → menor" },
  { value: 4, label: "Preço: menor → maior" },
  { value: 5, label: "Melhor comissão" },
]

export const catalogApi = {
  async search(params: {
    keyword?: string
    product_cat_id?: number
    sort_type?: CatalogSortType
    limit?: number
  }): Promise<CatalogSearchResponse> {
    const searchParams = new URLSearchParams()
    if (params.keyword) searchParams.append('keyword', params.keyword)
    if (params.product_cat_id !== undefined) searchParams.append('product_cat_id', String(params.product_cat_id))
    if (params.sort_type !== undefined) searchParams.append('sort_type', String(params.sort_type))
    if (params.limit !== undefined) searchParams.append('limit', String(params.limit))
    const query = searchParams.toString()
    return api.get<CatalogSearchResponse>(`/products/catalog-search${query ? `?${query}` : ''}`)
  },

  async categories(): Promise<CatalogCategoriesResponse> {
    return api.get<CatalogCategoriesResponse>('/products/catalog-categories')
  },
}
