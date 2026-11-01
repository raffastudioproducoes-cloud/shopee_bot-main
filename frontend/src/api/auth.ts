import { api, ApiError } from '../lib/api'
import { formatApiError } from '../lib/apiError'

export interface User {
  id: string
  username: string
  access: string
}

export interface LoginResponse {
  msg: string
}

export interface MeResponse {
  id: string
  username: string
  access: string
  /** Perfil ativo validado pelo backend (claim do cookie); null = sem perfil/token antigo. */
  profile_id: string | null
}

export interface ResetPasswordResponse {
  msg: string
}

export interface RegisterResponse {
  id: string
  username: string
  access: string
}

export interface RegistrationPendingResponse {
  msg: string
  email_confirmation_required: true
}

export const authApi = {
  async capabilities(): Promise<{ email_enabled: boolean; email_signup_enabled: boolean; google_enabled: boolean; legacy_support_enabled: boolean }> {
    return api.get('/auth/supabase/config')
  },

  async loginEmail(email: string, password: string): Promise<string> {
    const result = await api.post<LoginResponse>('/auth/supabase/login', { email, password })
    return result.msg
  },

  async completeGoogle(username: string): Promise<RegisterResponse> {
    return api.post<RegisterResponse>('/auth/supabase/google/complete', {
      username, accepted_terms_version: '2026-10-31',
    })
  },

  async login(username: string, password: string): Promise<string> {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)

    const response = await fetch('/api/auth/login', {
      method: 'POST',
      body: formData,
      credentials: 'include',
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Erro no login' }))
      throw new ApiError(response.status, formatApiError(error, response.status))
    }

    const data = await response.json()
    return data.msg
  },

  async logout(): Promise<void> {
    const response = await fetch('/api/auth/logout', {
      method: 'POST',
      credentials: 'include',
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Erro no logout' }))
      throw new ApiError(response.status, formatApiError(error, response.status))
    }
  },

  async me(): Promise<MeResponse> {
    return api.get<MeResponse>('/auth/me')
  },

  async requestPasswordRecovery(email: string): Promise<string> {
    const data = await api.post<ResetPasswordResponse>('/auth/supabase/password/recovery', { email })
    return data.msg
  },

  async completePasswordRecovery(accessToken: string, newPassword: string, confirmPassword: string): Promise<string> {
    const data = await api.post<ResetPasswordResponse>('/auth/supabase/password/complete', {
      access_token: accessToken,
      new_password: newPassword,
      confirm_password: confirmPassword,
    })
    return data.msg
  },

  async register(username: string, email: string, password: string, confirmPassword: string): Promise<RegistrationPendingResponse> {
    return api.post<RegistrationPendingResponse>('/auth/supabase/register', {
      username, email, password, confirm_password: confirmPassword,
      accepted_terms_version: '2026-10-31',
    })
  },
}