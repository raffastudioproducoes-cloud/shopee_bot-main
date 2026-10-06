import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { useProfileStore } from './profileStore'

export interface User {
  id: number
  username: string
  access: string
}

interface AuthState {
  accessToken: string | null
  user: User | null
  isAuthenticated: boolean
  login: (token: string, user: User) => void
  logout: () => void
  setUser: (user: User) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      user: null,
      isAuthenticated: false,
      login: (token: string, user: User) => {
        // novo login => backend emite cookie com o perfil principal
        useProfileStore.getState().setActiveProfileId(null)
        set({ accessToken: token, user, isAuthenticated: true })
      },
      logout: () => {
        useProfileStore.getState().setActiveProfileId(null)
        set({ accessToken: null, user: null, isAuthenticated: false })
      },
      setUser: (user: User) => {
        set({ user })
      },
    }),
    {
      name: 'shopee-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        accessToken: state.accessToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)