import { api } from '../lib/api'

export interface Product {
  id: number
  user_id: number
  product_id: string
  name: string
  description?: string | null
  original_link: string | null
  commission_link: string | null
  commission: number | string | null
  image: string | null
  price_min: number | string | null
  price_max: number | string | null
  category: string | null
  created_at: string
  updated_at: string | null
}

export interface ProductCreate {
  product_id: string
  name: string
  original_link: string
  commission_link: string
  commission?: number | string | null
  image?: string | null
  price_min?: number | string | null
  price_max?: number | string | null
  category?: string | null
}

export interface ProductUpdate {
  name?: string
  description?: string | null
}

export interface ProductMedia {
  id: string
  product_id: number
  media_type: "IMAGE" | "VIDEO"
  file_name: string
  size_bytes: number
  slot: number
  preview_url: string
  thumbnail_url?: string | null
}

export interface ProductsResponse {
  data: Product[]
  total: number
  page: number
  page_size: number
}

export const productsApi = {
  /** Download com cookie httpOnly, mesmo quando o backend usa origem distinta. */
  async downloadImage(id: number): Promise<{ blob: Blob; filename: string }> {
    const { blob, mimeType } = await api.download(`/products/${id}/image/download`)
    const extension = mimeType === 'image/png' ? '.png'
      : mimeType === 'image/webp' ? '.webp'
      : mimeType === 'image/gif' ? '.gif' : '.jpg'
    return { blob, filename: `shopee-produto-${id}${extension}` }
  },
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

  async media(id: number): Promise<{ items: ProductMedia[] }> {
    return api.get<{ items: ProductMedia[] }>(`/products/${id}/media`)
  },

  async uploadMedia(
    id: number, file: File,
    onProgress?: (loaded: number, total: number) => void,
    onTransferred?: () => void,
  ): Promise<ProductMedia> {
    if (onProgress) return api.uploadWithProgress<ProductMedia>(`/products/${id}/media`, file, onProgress, onTransferred)
    return api.upload<ProductMedia>(`/products/${id}/media`, file)
  },

  async deleteMedia(id: number, assetId: string): Promise<{ msg: string }> {
    return api.delete<{ msg: string }>(`/products/${id}/media/${assetId}`)
  },

  async delete(id: number, keepalive = false): Promise<{ msg: string }> {
    return api.delete<{ msg: string }>(`/products/${id}`, undefined, keepalive)
  },
}
