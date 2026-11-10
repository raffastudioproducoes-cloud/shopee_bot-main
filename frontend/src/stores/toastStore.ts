import { create } from 'zustand'

export type ToastKind = 'loading' | 'success' | 'error'

export interface Toast {
  id: string
  kind: ToastKind
  text: string
  /** Quantas vezes o mesmo aviso se repetiu (aparece como ×N). */
  count?: number
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
    // Mesmo texto e tipo com outro id (ex.: salvar três vezes seguidas): agrupa em um só aviso com ×N.
    const twin = get().toasts.find((t) => t.id !== toast.id && t.kind === toast.kind && t.text === toast.text && toast.kind !== 'loading')
    if (twin) {
      set({ toasts: get().toasts.map((t) => (t.id === twin.id ? { ...t, count: (t.count ?? 1) + 1 } : t)) })
      return
    }
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
