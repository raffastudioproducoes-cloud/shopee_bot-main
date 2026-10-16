import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { useProfileStore } from './profileStore'
import { clearAdminVisitingSite } from '../lib/adminSiteFlag'

export interface User {
  id: number
  username: string
  access: string
}

interface AuthState {
  accessToken: string | null
  user: User | null
  isAuthenticated: boolean
  isRoleVerified: boolean
  login: (token: string, user: User) => void
  logout: () => void
  setUser: (user: User) => void
  setRoleVerified: (isRoleVerified: boolean) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      user: null,
      isAuthenticated: false,
      isRoleVerified: false,
      login: (token: string, user: User) => {
        // novo login => backend emite cookie com o perfil principal
        useProfileStore.getState().setActiveProfileId(null)
        set({ accessToken: token, user, isAuthenticated: true, isRoleVerified: false })
      },
      logout: () => {
        clearAdminVisitingSite()
        useProfileStore.getState().setActiveProfileId(null)
        set({ accessToken: null, user: null, isAuthenticated: false, isRoleVerified: false })
      },
      setUser: (user: User) => {
        set({ user })
      },
      setRoleVerified: (isRoleVerified: boolean) => {
        set({ isRoleVerified })
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
