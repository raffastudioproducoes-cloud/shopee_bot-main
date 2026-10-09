import { formatApiError } from './apiError'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    credentials: 'include',
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new ApiError(response.status, formatApiError(error, response.status))
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}

export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint, { method: 'GET' }),
  post: <T>(endpoint: string, data: unknown) =>
    request<T>(endpoint, { method: 'POST', body: JSON.stringify(data) }),
  put: <T>(endpoint: string, data: unknown) =>
    request<T>(endpoint, { method: 'PUT', body: JSON.stringify(data) }),
  delete: <T>(endpoint: string, data?: unknown) =>
    request<T>(endpoint, { method: 'DELETE', ...(data !== undefined && { body: JSON.stringify(data) }) }),
  // multipart: sem Content-Type manual — o browser define com o boundary certo
  upload: async <T>(endpoint: string, file: File): Promise<T> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      body: formData,
      credentials: 'include',
    })
    if (!response.ok) {
      const error = await response.json().catch(() => null)
      throw new ApiError(response.status, formatApiError(error, response.status))
    }
    return response.json()
  },
}