import { useEffect, useRef, useState } from "react"
import { readFormDraft, saveFormDraft } from "../lib/formDraftStorage"

/**
 * Recupera um rascunho quando o escopo aparece/muda e salva após cada edição.
 * A restauração recebe null quando não há rascunho, para não misturar perfis.
 * Campos apagados são salvos como vazios; somente "Salvar" deve limpar a chave.
 */
export function useAutosavedDraft<T>(
  key: string | null,
  value: T,
  restore: (saved: T | null) => void,
): void {
  const restoreRef = useRef(restore)
  restoreRef.current = restore
  const valueRef = useRef(value)
  valueRef.current = value
  const [readyKey, setReadyKey] = useState<string | null>(null)
  // JSON somente de campos explícitos; não passe File, senha, token ou objetos de API.
  const serialized = JSON.stringify(value)

  useEffect(() => {
    if (!key) {
      setReadyKey(null)
      return
    }
    restoreRef.current(readFormDraft<T>(key))
    setReadyKey(key)
  }, [key])

  useEffect(() => {
    // A primeira renderização de uma nova chave ainda contém estado antigo:
    // só gravar depois da restauração para não sobrescrever o rascunho salvo.
    if (key && readyKey === key) saveFormDraft(key, valueRef.current)
  }, [key, readyKey, serialized])

  useEffect(() => {
    if (!key || readyKey !== key) return
    const flush = () => { saveFormDraft(key, valueRef.current) }
    window.addEventListener("pagehide", flush)
    return () => { window.removeEventListener("pagehide", flush) }
  }, [key, readyKey])
}
