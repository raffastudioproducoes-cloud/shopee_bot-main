import { useCallback, useState } from "react"
import type { CSSProperties } from "react"
import { IconButton } from "./IconButton"

export type ViewMode = "list" | "grid-small" | "grid-large"

const OPTIONS: { view: ViewMode; icon: string; label: string }[] = [
  { view: "list", icon: "list", label: "Lista" },
  { view: "grid-small", icon: "grid-3x3", label: "Grade pequena" },
  { view: "grid-large", icon: "layout-grid", label: "Grade grande" },
]

/** Modo de visualização persistido em localStorage (padrão Windows Explorer). */
export function useViewMode(storageKey: string): [ViewMode, (next: ViewMode) => void] {
  const [view, setView] = useState<ViewMode>(() => {
    try {
      const raw = localStorage.getItem(storageKey)
      if (raw === "list" || raw === "grid-small" || raw === "grid-large") return raw
    } catch {
      // localStorage indisponível (modo privado, etc.) — usa o padrão
    }
    return "list"
  })
  const change = useCallback(
    (next: ViewMode) => {
      setView(next)
      try {
        localStorage.setItem(storageKey, next)
      } catch {
        // a preferência só não persiste entre sessões
      }
    },
    [storageKey],
  )
  return [view, change]
}

/** Estilo do contêiner dos cards para cada modo. */
export function viewContainerStyle(view: ViewMode): CSSProperties {
  if (view === "list") return { display: "flex", flexDirection: "column", gap: 12 }
  return {
    display: "grid",
    gridTemplateColumns:
      view === "grid-small"
        ? "repeat(auto-fill, minmax(min(100%, 200px), 1fr))"
        : "repeat(auto-fill, minmax(min(100%, 340px), 1fr))",
    gap: 12,
    alignItems: "start",
  }
}

export function ViewSwitcher({ value, onChange }: { value: ViewMode; onChange: (v: ViewMode) => void }) {
  return (
    <div
      role="group"
      aria-label="Modo de visualização"
      style={{
        display: "inline-flex",
        gap: 2,
        padding: 3,
        background: "var(--surface-inset)",
        border: "1px solid var(--border-hairline)",
        borderRadius: "var(--r-pill)",
      }}
    >
      {OPTIONS.map((opt) => (
        <IconButton
          key={opt.view}
          icon={opt.icon}
          label={opt.label}
          tone="plain"
          size={30}
          active={value === opt.view}
          onClick={() => onChange(opt.view)}
        />
      ))}
    </div>
  )
}
