import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { useProfileStore } from './profileStore'
import { clearAdminVisitingSite } from '../lib/adminSiteFlag'

export interface User {
  id: string
  username: string
  access: string
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isRoleVerified: boolean
  login: (user: User) => void
  logout: () => void
  setUser: (user: User) => void
  setRoleVerified: (isRoleVerified: boolean) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isRoleVerified: false,
      login: (user: User) => {
        // novo login => backend emite cookie com o perfil principal
        useProfileStore.getState().setActiveProfileId(null)
        set({ user, isAuthenticated: true, isRoleVerified: false })
      },
      logout: () => {
        clearAdminVisitingSite()
        useProfileStore.getState().setActiveProfileId(null)
        set({ user: null, isAuthenticated: false, isRoleVerified: false })
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
      // O navegador não guarda token: a sessão é o cookie httpOnly e o estado local
      // é só cache de renderização, revalidado em /auth/me.
      version: 1,
      migrate: (persisted) => {
        const { accessToken: _legacyToken, ...rest } = (persisted ?? {}) as Record<string, unknown>
        return rest as never
      },
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
