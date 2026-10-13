import type { NetworkRule } from "./networkLimits"

/** Cópia de `list` com o item de `from` movido para `to` (índices inválidos = sem mudança). */
export function moveItem<T>(list: readonly T[], from: number, to: number): T[] {
  const out = [...list]
  if (from === to || from < 0 || to < 0 || from >= out.length || to >= out.length) return out
  const [item] = out.splice(from, 1)
  out.splice(to, 0, item)
  return out
}

/** Menor maxMedia entre as redes que entregam carrossel; undefined = sem limite conhecido. */
export function trayLimit(rules: readonly Pick<NetworkRule, "deliveredModes" | "maxMedia">[]): number | undefined {
  const limits = rules
    .filter((r) => r.deliveredModes.includes("carousel") && r.maxMedia != null)
    .map((r) => r.maxMedia as number)
  return limits.length ? Math.min(...limits) : undefined
}
