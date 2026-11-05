import { api } from '../lib/api'

export interface ProductList {
  id: number
  name: string
  created_at: string
  updated_at: string | null
  product_count: number
  products?: Product[]
}

export interface Product {
  id: number
  product_id: string
  name: string
  image: string | null
  price_min: number | string | null
  price_max: number | string | null
  commission: number | string | null
  commission_link: string | null
  original_link: string | null
}

export interface ProductListCreate {
  name: string
  product_ids?: number[]
}

export interface ProductListUpdate {
  name: string
  product_ids?: number[]
}

export interface ProductListsResponse {
  data: ProductList[]
  next_cursor: string | null
}

export interface ListUsageResponse {
  /** Campanhas ativadas por ID de lista (histórico da conta/perfil). */
  counts: Record<string, number>
}

export const listsApi = {
  async usage(): Promise<ListUsageResponse> {
    return api.get<ListUsageResponse>('/lists/usage')
  },

  async list(params?: { cursor?: string; limit?: number }): Promise<ProductListsResponse> {
    const searchParams = new URLSearchParams()
    if (params?.cursor) searchParams.append('cursor', params.cursor)
    if (params?.limit) searchParams.append('limit', String(params.limit))

    const query = searchParams.toString()
    return api.get<ProductListsResponse>(`/lists${query ? `?${query}` : ''}`)
  },

  async create(data: ProductListCreate): Promise<ProductList & { product_count?: number }> {
    return api.post<ProductList & { product_count?: number }>('/lists', data)
  },

  async get(id: number): Promise<ProductList> {
    return api.get<ProductList>(`/lists/${id}`)
  },

  async update(id: number, data: ProductListUpdate): Promise<ProductList> {
    return api.put<ProductList>(`/lists/${id}`, data)
  },

  async delete(id: number): Promise<{ msg: string }> {
    return api.delete<{ msg: string }>(`/lists/${id}`)
  },
}
