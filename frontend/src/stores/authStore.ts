/**
 * Store de autenticação — Zustand
 * Gerencia estado do usuário logado e operações de login/logout.
 */

import { create } from 'zustand'
import { login as apiLogin, logout as apiLogout, getMe } from '../lib/auth'

interface AuthState {
  user: {
    id: string
    username: string
    access: string
  } | null
  loading: boolean
  error: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  checkAuth: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  loading: false,
  error: null,

  login: async (username: string, password: string) => {
    set({ loading: true, error: null })
    try {
      await apiLogin(username, password)
      const user = await getMe()
      if (user) {
        set({ user, loading: false })
      } else {
        set({ loading: false, error: 'Erro ao carregar perfil' })
      }
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : 'Erro ao fazer login',
      })
    }
  },

  logout: async () => {
    set({ loading: true, error: null })
    try {
      await apiLogout()
      set({ user: null, loading: false })
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : 'Erro ao fazer logout',
      })
    }
  },

  checkAuth: async () => {
    set({ loading: true })
    try {
      const user = await getMe()
      set({ user, loading: false })
    } catch {
      set({ user: null, loading: false })
    }
  },
}))
