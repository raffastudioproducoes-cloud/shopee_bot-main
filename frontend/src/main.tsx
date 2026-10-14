import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from '@tanstack/react-router'
import { MutationCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { router } from './router'
import { ApiError } from './lib/api'
import { useToastStore, type MutationToastMeta } from './stores/toastStore'
import { Toaster } from './components/ui/Toaster'
import { APP_VERSION } from './appMeta'
import './index.css'

// Avisos de progresso globais: qualquer mutation com `meta.toast` mostra
// "pending" → "success" / erro legível, sem cada página reimplementar.
const toastMeta = (meta: Record<string, unknown> | undefined) => meta?.toast as MutationToastMeta | undefined
const toastId = (mutationId: number) => `mutation-${mutationId}`

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
  mutationCache: new MutationCache({
    onMutate: (_vars, mutation) => {
      const t = toastMeta(mutation.meta)
      if (t?.pending) useToastStore.getState().show({ id: toastId(mutation.mutationId), kind: 'loading', text: t.pending })
    },
    onSuccess: (data, _vars, _ctx, mutation) => {
      const t = toastMeta(mutation.meta)
      if (!t) return
      const id = toastId(mutation.mutationId)
      const text = typeof t.success === 'function' ? t.success(data) : t.success
      if (text) useToastStore.getState().show({ id, kind: 'success', text })
      else useToastStore.getState().dismiss(id)
    },
    onError: (error, _vars, _ctx, mutation) => {
      const t = toastMeta(mutation.meta)
      if (!t) return
      const id = toastId(mutation.mutationId)
      // 401 já redireciona pro login — sem aviso.
      if (error instanceof ApiError && error.status === 401) return useToastStore.getState().dismiss(id)
      const text = t.error ? `${t.error}: ${error.message}` : error.message
      useToastStore.getState().show({ id, kind: 'error', text })
    },
  }),
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster />
    </QueryClientProvider>
  </React.StrictMode>,
)

// PWA: registra o service worker só em produção; ?v= muda a cada release e renova o cache.
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register(`/sw.js?v=${encodeURIComponent(APP_VERSION)}`).catch(() => {})
  })
}
