// Rascunhos locais do navegador. Nunca usar para senhas, tokens, OAuth ou File.
// O backend continua a única fonte da verdade após "Salvar".
const PREFIX = "auto-orbital:form-draft:v1:"
const VERSION = 1
const MAX_AGE_MS = 90 * 24 * 60 * 60 * 1000
const MAX_BYTES = 256 * 1024

interface SavedDraft<T> {
  version: number
  savedAt: number
  value: T
}

export function formDraftKey(
  accountId: string | null | undefined,
  form: string,
  profileId?: string | null,
  scopedToProfile = true,
): string | null {
  if (!accountId || (scopedToProfile && !profileId)) return null
  const parts = [accountId, scopedToProfile ? profileId! : "account", form]
  return PREFIX + parts.map((part) => encodeURIComponent(part)).join(":")
}

export function readFormDraft<T>(key: string | null): T | null {
  if (!key) return null
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return null
    const saved = JSON.parse(raw) as SavedDraft<T>
    if (!saved || saved.version !== VERSION ||
        typeof saved.savedAt !== "number" || !Number.isFinite(saved.savedAt) ||
        saved.savedAt > Date.now() + 60_000 ||
        Date.now() - saved.savedAt > MAX_AGE_MS ||
        !Object.prototype.hasOwnProperty.call(saved, "value")) {
      localStorage.removeItem(key)
      return null
    }
    return saved.value
  } catch {
    // Navegação privada, quota ou dado corrompido nunca derrubam o formulário.
    return null
  }
}

export function saveFormDraft<T>(key: string | null, value: T): boolean {
  if (!key) return false
  try {
    const payload = JSON.stringify({ version: VERSION, savedAt: Date.now(), value } satisfies SavedDraft<T>)
    if (payload.length > MAX_BYTES) return false
    localStorage.setItem(key, payload)
    return true
  } catch {
    return false
  }
}

export function clearFormDraft(key: string | null): void {
  if (!key) return
  try {
    localStorage.removeItem(key)
  } catch {
    // Storage desabilitado: nada a remover.
  }
}
