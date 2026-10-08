/** Normaliza o corpo de erro da API (FastAPI) num texto legível em pt-BR.
 *
 * Formatos tratados: `detail` string; `detail` lista de erros de validação
 * 422 do Pydantic (`{loc, msg, type}`); objetos `{message}` / `{detail}`.
 * Nunca devolve "[object Object]". */

const FIELD_LABELS: Record<string, string> = {
  product_id: "ID Shopee",
  name: "Nome",
  original_link: "Link original",
  commission_link: "Link de comissão",
  commission: "Comissão",
  image: "Imagem",
  price_min: "Preço mínimo",
  price_max: "Preço máximo",
  product_ids: "Produtos",
  texts: "Textos",
  schedule: "Agendamento",
  network: "Rede",
  email: "E-mail",
  password: "Senha",
}

interface ValidationItem {
  loc?: unknown[]
  msg?: unknown
  type?: unknown
  ctx?: Record<string, unknown>
}

function translateMsg(item: ValidationItem): string {
  const type = typeof item.type === "string" ? item.type : ""
  const msg = typeof item.msg === "string" ? item.msg : ""
  if (type === "missing") return "campo obrigatório"
  if (type === "string_type") return "deve ser um texto"
  if (type === "float_parsing" || type === "float_type" || type === "int_parsing" || type === "int_type") return "deve ser um número"
  if (type === "decimal_max_places") return `informe no máximo ${item.ctx?.decimal_places ?? 2} casas decimais`
  if (type === "string_too_long") return `máximo de ${item.ctx?.max_length ?? "?"} caracteres`
  if (type === "string_too_short") return `mínimo de ${item.ctx?.min_length ?? "?"} caracteres`
  if (type.startsWith("greater_than") || type.startsWith("less_than")) return `valor fora do limite permitido`
  // Mensagens de validators do backend (já em pt-BR) vêm com prefixo do Pydantic.
  return msg.replace(/^Value error, /, "") || "valor inválido"
}

function formatValidationItem(item: unknown): string {
  if (typeof item === "string") return item
  if (!item || typeof item !== "object") return ""
  const v = item as ValidationItem
  const loc = Array.isArray(v.loc) ? v.loc.filter((p) => p !== "body" && p !== "query" && p !== "path") : []
  const field = loc.length ? String(loc[loc.length - 1]) : ""
  const label = FIELD_LABELS[field] ?? field
  const text = translateMsg(v)
  return label ? `${label}: ${text}` : text
}

export function formatApiError(body: unknown, status?: number): string {
  const fallback = status ? `Erro inesperado (HTTP ${status}). Tente novamente.` : "Erro inesperado. Tente novamente."
  if (body == null) return fallback
  if (typeof body === "string") return body.trim() || fallback
  if (Array.isArray(body)) {
    const parts = body.map(formatValidationItem).filter(Boolean)
    return parts.length ? parts.join(" · ") : fallback
  }
  if (typeof body === "object") {
    const obj = body as Record<string, unknown>
    if ("detail" in obj) return formatApiError(obj.detail, status)
    if (typeof obj.message === "string" && obj.message) return obj.message
  }
  return fallback
}
