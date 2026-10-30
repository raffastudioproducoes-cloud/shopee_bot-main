// Máscaras e validação pt-BR para data (dd/mm/aaaa) e hora (hh:mm, 24h).
// O estado da tela guarda o texto digitado; a API continua recebendo ISO/HH:MM.

const digits = (raw: string) => raw.replace(/\D/g, "")

export function maskDate(raw: string): string {
  const d = digits(raw).slice(0, 8)
  if (d.length <= 2) return d
  if (d.length <= 4) return `${d.slice(0, 2)}/${d.slice(2)}`
  return `${d.slice(0, 2)}/${d.slice(2, 4)}/${d.slice(4)}`
}

export function maskTime(raw: string): string {
  const d = digits(raw).slice(0, 4)
  return d.length <= 2 ? d : `${d.slice(0, 2)}:${d.slice(2)}`
}

/** "dd/mm/aaaa" -> "aaaa-mm-dd" se for um dia real do calendário; senão null. */
export function parseDate(text: string): string | null {
  const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(text)
  if (!m) return null
  const [day, month, year] = [Number(m[1]), Number(m[2]), Number(m[3])]
  const d = new Date(Date.UTC(year, month - 1, day))
  const real = d.getUTCFullYear() === year && d.getUTCMonth() === month - 1 && d.getUTCDate() === day
  return real ? `${m[3]}-${m[2]}-${m[1]}` : null
}

/** "hh:mm" (00:00–23:59) -> o mesmo texto; senão null. */
export function parseTime(text: string): string | null {
  const m = /^(\d{2}):(\d{2})$/.exec(text)
  return m && Number(m[1]) < 24 && Number(m[2]) < 60 ? text : null
}

/** "aaaa-mm-dd" -> "dd/mm/aaaa". */
export function isoToBr(iso: string): string {
  const [y, m, d] = iso.split("-")
  return `${d}/${m}/${y}`
}


/**
 * Converte timestamps UTC do PostgreSQL para Brasília.
 * Aceita valores com Z, offset explícito ou sem fuso.
 *
 * IMPORTANTE: timestamps sem fuso devem representar UTC.
 */
export function formatUtcTimestampBrasilia(value: string): string {
  const normalized = value.trim().replace(" ", "T")

  const hasTimezone = /(Z|[+-]\d{2}:?\d{2})$/i.test(normalized)
  const iso = hasTimezone ? normalized : `${normalized}Z`

  const date = new Date(iso)

  if (Number.isNaN(date.getTime())) {
    return "Data inválida"
  }

  return date.toLocaleString("pt-BR", {
    timeZone: "America/Sao_Paulo",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  })
}
