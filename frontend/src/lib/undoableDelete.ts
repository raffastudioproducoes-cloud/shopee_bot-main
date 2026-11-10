import { useMemo, useSyncExternalStore } from 'react'
import { useToastStore } from '../stores/toastStore'

/**
 * Exclusão com "Desfazer": o item some da lista na hora e a exclusão real só
 * é enviada ao servidor depois de UNDO_WINDOW_MS. Se a pessoa tocar em
 * "Desfazer", nada é enviado e o item volta. Se ela fechar a aba/navegar para
 * fora, a exclusão pendente é enviada na hora (fetch keepalive).
 */
export const UNDO_WINDOW_MS = 7000

interface Pending {
  timer: ReturnType<typeof setTimeout>
  run: (keepalive: boolean) => Promise<unknown>
  onSettled: (ok: boolean) => unknown
  toastId: string
}

const pending = new Map<string, Pending>()
let hidden: ReadonlySet<string> = new Set()
const listeners = new Set<() => void>()

function setHidden(next: Set<string>) {
  hidden = next
  listeners.forEach((l) => l())
}
const hide = (key: string) => setHidden(new Set(hidden).add(key))
const unhide = (key: string) => { const n = new Set(hidden); n.delete(key); setHidden(n) }

const itemKey = (kind: string, id: number | string) => `${kind}:${id}`

/** IDs de `kind` escondidos porque a exclusão está na janela de "Desfazer". */
export function useHiddenIds(kind: string): ReadonlySet<string> {
  const snapshot = useSyncExternalStore(
    (l) => { listeners.add(l); return () => { listeners.delete(l) } },
    () => hidden,
    () => hidden,
  )
  return useMemo(() => hiddenFor(kind, snapshot), [kind, snapshot])
}

function hiddenFor(kind: string, all: ReadonlySet<string>): ReadonlySet<string> {
  const prefix = `${kind}:`
  const out = new Set<string>()
  all.forEach((k) => { if (k.startsWith(prefix)) out.add(k.slice(prefix.length)) })
  return out
}

export function isPendingDelete(kind: string, id: number | string) {
  return pending.has(itemKey(kind, id))
}

async function commit(key: string, keepalive: boolean) {
  const p = pending.get(key)
  if (!p) return
  clearTimeout(p.timer)
  pending.delete(key)
  let ok = true
  try { await p.run(keepalive) } catch { ok = false }
  // Só volta a mostrar o item (se falhou) depois de a lista recarregar, sem piscar.
  try { await p.onSettled(ok) } finally { unhide(key) }
}

export function undoDelete(kind: string, id: number | string) {
  const key = itemKey(kind, id)
  const p = pending.get(key)
  if (!p) return
  clearTimeout(p.timer)
  pending.delete(key)
  unhide(key)
  useToastStore.getState().dismiss(p.toastId)
}

export interface ScheduleOptions {
  kind: string
  id: number | string
  /** Texto do aviso, ex.: "Post removido". */
  message: string
  /** Falha do servidor: texto do aviso de erro. */
  errorMessage: string
  /** Faz a exclusão de verdade. */
  run: (keepalive: boolean) => Promise<unknown>
  /** Depois de concluída (ok=true) ou falha (ok=false): invalidar listas etc. */
  onSettled?: (ok: boolean) => unknown
  windowMs?: number
}

export function scheduleUndoableDelete(opts: ScheduleOptions) {
  const key = itemKey(opts.kind, opts.id)
  if (pending.has(key)) return
  const toastId = `undo-${key}`
  const windowMs = opts.windowMs ?? UNDO_WINDOW_MS
  hide(key)
  const timer = setTimeout(() => { void commit(key, false) }, windowMs)
  pending.set(key, {
    timer,
    run: opts.run,
    toastId,
    onSettled: (ok) => {
      if (!ok) useToastStore.getState().show({ id: `${toastId}-err`, kind: 'error', text: opts.errorMessage })
      return opts.onSettled?.(ok)
    },
  })
  useToastStore.getState().show({
    id: toastId,
    kind: 'success',
    text: opts.message,
    durationMs: windowMs,
    action: { label: 'Desfazer', onClick: () => undoDelete(opts.kind, opts.id) },
  })
}

/** Envia na hora tudo que ainda está na janela de "Desfazer". */
export function flushPendingDeletes(keepalive = true) {
  for (const key of [...pending.keys()]) void commit(key, keepalive)
}

if (typeof window !== 'undefined') {
  window.addEventListener('pagehide', () => flushPendingDeletes(true))
}
