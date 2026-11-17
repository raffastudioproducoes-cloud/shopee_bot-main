import { useEffect, useState } from "react"

// Idioma das páginas públicas (landing e páginas legais): português ou inglês.
// Ordem: ?lang= na URL, escolha salva no navegador, idioma do navegador.
export type SiteLang = "pt" | "en"

const STORAGE_KEY = "ao-site-lang"

export function pickSiteLang(query: string | null, saved: string | null, browser: string | undefined): SiteLang {
  for (const value of [query, saved]) {
    if (value === "pt" || value === "en") return value
  }
  return (browser ?? "pt").toLowerCase().startsWith("pt") ? "pt" : "en"
}

function initialLang(): SiteLang {
  let saved: string | null = null
  try { saved = window.localStorage.getItem(STORAGE_KEY) } catch { /* navegador sem armazenamento */ }
  return pickSiteLang(new URLSearchParams(window.location.search).get("lang"), saved, window.navigator.language)
}

export function useSiteLang(): [SiteLang, (lang: SiteLang) => void] {
  const [lang, setLang] = useState<SiteLang>(initialLang)

  useEffect(() => {
    const previous = document.documentElement.lang
    document.documentElement.lang = lang === "en" ? "en" : "pt-BR"
    return () => { document.documentElement.lang = previous }
  }, [lang])

  const choose = (next: SiteLang) => {
    setLang(next)
    try { window.localStorage.setItem(STORAGE_KEY, next) } catch { /* navegador sem armazenamento */ }
  }
  return [lang, choose]
}
