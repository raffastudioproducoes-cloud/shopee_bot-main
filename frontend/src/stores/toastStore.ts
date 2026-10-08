import { create } from 'zustand'

export type ToastKind = 'loading' | 'success' | 'error'

export interface Toast {
  id: string
  kind: ToastKind
  text: string
}

interface ToastState {
  toasts: Toast[]
  /** Cria ou substitui (mesmo id) um aviso. Sucesso some sozinho; erro fica até fechar. */
  show: (toast: Toast) => void
  dismiss: (id: string) => void
}

const SUCCESS_TIMEOUT_MS = 4000

export const useToastStore = create<ToastState>()((set, get) => ({
  toasts: [],
  show: (toast) => {
    set({ toasts: [...get().toasts.filter((t) => t.id !== toast.id), toast] })
    if (toast.kind === 'success') {
      setTimeout(() => {
        // só remove se ainda for o mesmo aviso de sucesso (id pode ter sido reaproveitado)
        if (get().toasts.some((t) => t.id === toast.id && t.kind === 'success')) get().dismiss(toast.id)
      }, SUCCESS_TIMEOUT_MS)
    }
  },
  dismiss: (id) => set({ toasts: get().toasts.filter((t) => t.id !== id) }),
}))

/** Textos de progresso de uma mutation (react-query `meta.toast`). */
export interface MutationToastMeta {
  pending?: string
  success?: string | ((data: unknown) => string | null)
  /** Prefixo do erro, ex.: "Não foi possível salvar". */
  error?: string
}
