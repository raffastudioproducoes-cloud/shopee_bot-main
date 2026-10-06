import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

// O backend nao expoe o perfil ativo (o claim vive no cookie httponly), entao o
// front guarda o ultimo id ativado. Sem valor (ou id inexistente) = principal.
interface ProfileState {
  activeProfileId: string | null
  setActiveProfileId: (id: string | null) => void
}

export const useProfileStore = create<ProfileState>()(
  persist(
    (set) => ({
      activeProfileId: null,
      setActiveProfileId: (id) => set({ activeProfileId: id }),
    }),
    { name: 'shopee-active-profile', storage: createJSONStorage(() => localStorage) }
  )
)
