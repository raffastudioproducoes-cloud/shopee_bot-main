/** Descrição padrão herdada do catálogo; não altera o produto nem o rascunho. */
export function inheritProductCopy(
  current: string,
  previousInherited: string | null,
  savedDescription: string | null | undefined,
): string {
  const next = savedDescription?.trim() ?? ""
  // O texto digitado/gerado na postagem tem sempre precedência.
  if (current.trim() && (previousInherited === null || current !== previousInherited)) return current
  return next
}
