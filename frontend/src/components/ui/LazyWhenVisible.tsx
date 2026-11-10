import { useEffect, useRef, useState } from "react"
import type { ReactNode } from "react"

/**
 * Só monta os filhos quando a área chega perto da tela (uma vez). Evita disparar consultas pesadas
 * (ex.: análises embaixo do dashboard) para quem nunca rola até lá. Sem IntersectionObserver, monta direto.
 */
export function LazyWhenVisible({ children, placeholder, rootMargin = "300px" }: { children: ReactNode; placeholder: ReactNode; rootMargin?: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(() => typeof IntersectionObserver === "undefined")

  useEffect(() => {
    if (visible || !ref.current) return
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        setVisible(true)
        observer.disconnect()
      }
    }, { rootMargin })
    observer.observe(ref.current)
    return () => observer.disconnect()
  }, [visible, rootMargin])

  return <div ref={ref}>{visible ? children : placeholder}</div>
}
