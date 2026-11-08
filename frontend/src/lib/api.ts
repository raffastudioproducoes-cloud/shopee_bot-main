import { formatApiError } from './apiError'
import { useAuthStore } from '../stores/authStore'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

let revalidatingRole = false

// 403 em rota /admin: o papel pode ter mudado. Revalida /auth/me e, se deixou de
// ser ADMIN, volta ao site. Sem redirecionar quando ainda é ADMIN (evita loop).
async function onAdminForbidden() {
  if (revalidatingRole) return
  revalidatingRole = true
  try {
    const store = useAuthStore.getState()
    store.setRoleVerified(false)
    const res = await fetch(`${API_BASE}/auth/me`, { credentials: 'include' })
    if (res.status === 401) {
      store.logout()
      window.location.assign('/login')
      return
    }
    if (!res.ok) {
      // Uma indisponibilidade 5xx/429 não prova revogação do cookie.
      store.setRoleVerified(true)
      return
    }
    const me = await res.json()
    store.setUser(me)
    if (me.access !== 'ADMIN') {
      window.location.assign('/')
    } else {
      store.setRoleVerified(true)
    }
  } catch {
    useAuthStore.getState().setRoleVerified(true)
  } finally {
    revalidatingRole = false
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
    if (response.status === 403 && endpoint.startsWith('/admin')) void onAdminForbidden()
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
  download: async (endpoint: string): Promise<{ blob: Blob; mimeType: string }> => {
    const response = await fetch(`${API_BASE}${endpoint}`, { method: 'GET', credentials: 'include' })
    if (!response.ok) {
      const error = await response.json().catch(() => null)
      throw new ApiError(response.status, formatApiError(error, response.status))
    }
    return { blob: await response.blob(), mimeType: response.headers.get('content-type')?.split(';')[0] ?? '' }
  },
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
