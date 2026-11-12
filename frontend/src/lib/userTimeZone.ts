// Fuso horário do usuário (nome IANA) para agendar e exibir horários.
// A API guarda o valor em users.timezone; aqui fica a cópia em uso pela tela.
// Sem imports de propósito: os testes em node carregam este arquivo direto.

export const DEFAULT_TIME_ZONE = "America/Sao_Paulo"
const STORAGE_KEY = "orbital-time-zone"

export function isValidTimeZone(value: unknown): value is string {
  if (typeof value !== "string" || !value || value.length > 64) return false
  try {
    new Intl.DateTimeFormat("en-US", { timeZone: value })
    return true
  } catch {
    return false
  }
}

/** Fuso do PC/celular; navegador sem suporte cai no padrão histórico. */
export function deviceTimeZone(): string {
  try {
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone
    return isValidTimeZone(zone) ? zone : DEFAULT_TIME_ZONE
  } catch {
    return DEFAULT_TIME_ZONE
  }
}

function cachedTimeZone(): string | null {
  try {
    const value = globalThis.localStorage?.getItem(STORAGE_KEY)
    return isValidTimeZone(value) ? value : null
  } catch {
    return null
  }
}

let current = cachedTimeZone() ?? deviceTimeZone()

export function getUserTimeZone(): string {
  return current
}

export function setUserTimeZone(zone: string): void {
  if (!isValidTimeZone(zone)) return
  current = zone
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, zone)
  } catch {
    // Armazenamento bloqueado: vale só nesta aba até o próximo /auth/me.
  }
}

/** Usuário que nunca confirmou um fuso adota o do dispositivo (uma vez). */
export function shouldAdoptDeviceTimeZone(
  me: { timezone?: string | null; timezone_confirmed?: boolean | null },
  device: string,
): boolean {
  return me.timezone_confirmed === false && isValidTimeZone(device) && device !== me.timezone
}

/** Lista IANA do navegador para o seletor; sempre inclui o atual e o padrão. */
export function supportedTimeZones(): string[] {
  const intl = Intl as unknown as { supportedValuesOf?: (key: string) => string[] }
  let zones: string[] = []
  try {
    zones = intl.supportedValuesOf?.("timeZone") ?? []
  } catch {
    zones = []
  }
  return [...new Set([...zones, current, DEFAULT_TIME_ZONE, "UTC"])].sort()
}

/** "09:00 (Europe/Lisbon)": horário recorrente com o fuso em que dispara. */
export function withTimeZone(clock: string, zone: string = current): string {
  return `${clock} (${zone})`
}

/** Instante (ISO, epoch ou Date) no fuso do usuário. */
export function formatInstant(
  value: string | number | Date,
  options: Intl.DateTimeFormatOptions = {},
): string {
  return new Date(value).toLocaleString("pt-BR", { ...options, timeZone: current })
}

/**
 * Timestamps do PostgreSQL no fuso do usuário. Aceita Z, offset explícito
 * ou valor sem fuso, que deve representar UTC.
 */
export function formatUtcTimestamp(value: string): string {
  const normalized = value.trim().replace(" ", "T")
  const hasTimezone = /(Z|[+-]\d{2}:?\d{2})$/i.test(normalized)
  const date = new Date(hasTimezone ? normalized : `${normalized}Z`)
  if (Number.isNaN(date.getTime())) return "Data inválida"
  return formatInstant(date, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  })
}
