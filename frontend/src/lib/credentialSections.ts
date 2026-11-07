/** Agrupa por cadastro real, não pela cor ou validade do último teste. */
export function groupCredentialCards<T extends { title: string; connected: boolean }>(cards: readonly T[]): {
  registered: T[]
  pending: T[]
} {
  const collator = new Intl.Collator("pt-BR", { sensitivity: "base" })
  const ordered = [...cards].sort((a, b) => collator.compare(a.title, b.title))
  return {
    registered: ordered.filter((card) => card.connected),
    pending: ordered.filter((card) => !card.connected),
  }
}
