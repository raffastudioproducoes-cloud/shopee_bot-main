/** `commission` em todo o app = TAXA de comissão em % (6 = 6%), não R$.
 * Ganho estimado por venda = preço × taxa (doc productOfferV2 da Shopee:
 * `commission` = preço × `commissionRate`). */

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" })
const pct = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 })

export function toNumber(value: number | string | null | undefined): number | null {
  if (value == null || value === "") return null
  // O backend guarda preço/comissão como TEXT: aceita "49.99" e "49,99".
  const n = typeof value === "string" ? Number(value.includes(",") ? value.replace(/\./g, "").replace(",", ".") : value) : value
  return Number.isFinite(n) ? n : null
}

export const round2 = (n: number) => Math.round(n * 100) / 100

export const formatBRL = (n: number) => brl.format(n)

export function formatRate(rate: number | string | null | undefined): string {
  const r = toNumber(rate)
  return r == null ? "—" : `${pct.format(r)}%`
}

export function formatPriceRange(min: number | string | null | undefined, max: number | string | null | undefined): string {
  const lo = toNumber(min)
  const hi = toNumber(max)
  if (lo != null && hi != null && round2(lo) !== round2(hi)) return `${formatBRL(lo)} – ${formatBRL(hi)}`
  if (lo != null) return formatBRL(lo)
  if (hi != null) return formatBRL(hi)
  return "—"
}

/** Ganho estimado por venda (R$), faixa quando o preço varia. */
export function formatEarnings(
  min: number | string | null | undefined,
  max: number | string | null | undefined,
  rate: number | string | null | undefined,
): string {
  const r = toNumber(rate)
  if (r == null) return "—"
  const lo = toNumber(min)
  const hi = toNumber(max)
  return formatPriceRange(lo != null ? (lo * r) / 100 : null, hi != null ? (hi * r) / 100 : null)
}
