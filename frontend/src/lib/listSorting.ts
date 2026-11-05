/** Critérios de ordenação de Listas. Sem efeitos colaterais nem chamadas externas. */
export type ListSortMode =
  | "name-asc" | "name-desc"
  | "created-asc" | "created-desc"
  | "items-asc" | "items-desc"
  | "updated-asc" | "updated-desc"
  | "usage-asc" | "usage-desc"

export const LIST_SORT_OPTIONS: { value: ListSortMode; label: string }[] = [
  { value: "name-asc", label: "Nome: A → Z" },
  { value: "name-desc", label: "Nome: Z → A" },
  { value: "created-desc", label: "Criação: mais recentes" },
  { value: "created-asc", label: "Criação: mais antigas" },
  { value: "items-desc", label: "Produtos: mais itens" },
  { value: "items-asc", label: "Produtos: menos itens" },
  { value: "updated-desc", label: "Edição: mais novas" },
  { value: "updated-asc", label: "Edição: mais antigas" },
  { value: "usage-desc", label: "Uso: mais campanhas ativadas" },
  { value: "usage-asc", label: "Uso: menos campanhas ativadas" },
]

export const DEFAULT_LIST_SORT: ListSortMode = "created-desc"

export function isListSortMode(value: string | null): value is ListSortMode {
  return LIST_SORT_OPTIONS.some((option) => option.value === value)
}

export function isUsageSort(mode: ListSortMode): boolean {
  return mode === "usage-asc" || mode === "usage-desc"
}

export interface SortableList {
  id: number
  name: string
  created_at: string
  updated_at: string | null
  product_count: number
}

const collator = new Intl.Collator("pt-BR", { sensitivity: "base", numeric: true })

function timestamp(value: string | null): number {
  const parsed = value ? Date.parse(value) : NaN
  return Number.isFinite(parsed) ? parsed : 0
}

/** Cópia ordenada, preservando o array da query e desempate determinístico. */
export function sortProductLists<T extends SortableList>(
  lists: readonly T[],
  mode: ListSortMode,
  usageCounts: Readonly<Record<string, number>> = {},
): T[] {
  return [...lists].sort((a, b) => {
    const direction = mode.endsWith("-asc") ? 1 : -1
    let delta = 0
    if (mode.startsWith("name-")) delta = collator.compare(a.name, b.name)
    else if (mode.startsWith("created-")) delta = timestamp(a.created_at) - timestamp(b.created_at)
    else if (mode.startsWith("updated-")) {
      // Lista nunca editada: a última alteração conhecida é a própria criação.
      delta = timestamp(a.updated_at ?? a.created_at) - timestamp(b.updated_at ?? b.created_at)
    } else if (mode.startsWith("items-")) delta = (a.product_count ?? 0) - (b.product_count ?? 0)
    else if (isUsageSort(mode)) delta = (usageCounts[a.id] ?? 0) - (usageCounts[b.id] ?? 0)
    if (delta !== 0) return Math.sign(delta) * direction
    return collator.compare(a.name, b.name) || a.id - b.id
  })
}
