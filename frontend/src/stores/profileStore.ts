import { create } from 'zustand'

// Espelho em memoria do perfil ativo. A fonte da verdade e o `profile_id` de
// `/auth/me` (claim do cookie httponly); nada e persistido no navegador.
interface ProfileState {
  activeProfileId: string | null
  setActiveProfileId: (id: string | null) => void
}

export const useProfileStore = create<ProfileState>()((set) => ({
  activeProfileId: null,
  setActiveProfileId: (id) => set({ activeProfileId: id }),
}))
