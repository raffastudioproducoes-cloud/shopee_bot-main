import { api, ApiError } from '../lib/api'

export interface Product {
  id: number
  user_id: number
  product_id: string
  name: string
  original_link: string | null
  commission_link: string | null
  commission: number | null
  image: string | null
  price_min: number | null
  price_max: number | null
  category: string | null
  created_at: string
  updated_at: string | null
}

export interface ProductCreate {
  product_id: string
  name: string
  original_link?: string | null
  commission_link?: string | null
  commission?: number | null
  image?: string | null
  price_min?: number | null
  price_max?: number | null
  category?: string | null
}

export interface ProductUpdate {
  product_id?: string | null
  name?: string | null
  original_link?: string | null
  commission_link?: string | null
  commission?: number | null
  image?: string | null
  price_min?: number | null
  price_max?: number | null
  category?: string | null
}

export interface ProductsResponse {
  data: Product[]
  total: number
  page: number
  page_size: number
}

export const productsApi = {
  async list(params?: {
    search?: string
    category?: string
    min_price?: number
    max_price?: number
    sort_by?: string
    sort_order?: string
    page?: number
    page_size?: number
  }): Promise<ProductsResponse> {
    const searchParams = new URLSearchParams()
    if (params?.search) searchParams.append('search', params.search)
    if (params?.category) searchParams.append('category', params.category)
    if (params?.min_price !== undefined) searchParams.append('min_price', String(params.min_price))
    if (params?.max_price !== undefined) searchParams.append('max_price', String(params.max_price))
    if (params?.sort_by) searchParams.append('sort_by', params.sort_by)
    if (params?.sort_order) searchParams.append('sort_order', params.sort_order)
    if (params?.page) searchParams.append('page', String(params.page))
    if (params?.page_size) searchParams.append('page_size', String(params.page_size))

    const query = searchParams.toString()
    return api.get<ProductsResponse>(`/products${query ? `?${query}` : ''}`)
  },

  async create(data: ProductCreate): Promise<Product> {
    return api.post<Product>('/products', data)
  },

  async get(id: number): Promise<Product> {
    return api.get<Product>(`/products/${id}`)
  },

  async update(id: number, data: ProductUpdate): Promise<Product> {
    return api.put<Product>(`/products/${id}`, data)
  },

  async delete(id: number): Promise<{ msg: string }> {
    return api.delete<{ msg: string }>(`/products/${id}`)
  },
}

export { ApiError }