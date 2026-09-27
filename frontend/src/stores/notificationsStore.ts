import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

// Não há coluna "lido/não lido" em `activities` (ver api/routers/notifications.py) —
// o cliente decide o que é novo comparando created_at com o timestamp da última vez
// que o dropdown foi aberto, guardado aqui (mesmo padrão de persistência do authStore).
interface NotificationsState {
  lastSeenAt: string | null
  markSeen: (timestamp: string) => void
}

export const useNotificationsStore = create<NotificationsState>()(
  persist(
    (set) => ({
      lastSeenAt: null,
      markSeen: (timestamp: string) => set({ lastSeenAt: timestamp }),
    }),
    {
      name: 'shopee-notifications-seen',
      storage: createJSONStorage(() => localStorage),
    }
  )
)
