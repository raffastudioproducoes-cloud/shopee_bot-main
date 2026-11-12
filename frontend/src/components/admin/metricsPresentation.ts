import { getUserTimeZone } from "../../lib/userTimeZone"
export function formatMetricTime(timestamp: string) {
  const date = new Date(timestamp)
  return Number.isFinite(date.getTime()) ? date.toLocaleString('pt-BR', { timeZone: getUserTimeZone() }) : 'Horário indisponível'
}

export function isStale(timestamp: string, maximumAge = 300_000, now = Date.now()) {
  const time = Date.parse(timestamp)
  return !Number.isFinite(time) || now - time > maximumAge || time - now > 120_000
}

export function comparisonDelta(current: number, previous: number) {
  if (previous === 0) return current === 0 ? 'Sem variação' : 'Sem base percentual'
  const percent = (current - previous) / previous * 100
  return `${percent > 0 ? '+' : ''}${percent.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
}

export function capacityPercent(usage: { value: number; unit: string; timestamp: string } | null, limit: { value: number; unit: string; timestamp: string } | null) {
  if (!usage || !limit || !Number.isFinite(usage.value) || !Number.isFinite(limit.value) || usage.value < 0 || limit.value <= 0) return null
  const factors: Record<string, number> = { bytes: 1, byte: 1, B: 1, mb: 1e6, MB: 1e6, GB: 1e9, MiB: 1048576, GiB: 1073741824 }
  const cpu = new Set(['CPU', 'cpu', 'cores', 'core'])
  const delta = Math.abs(Date.parse(usage.timestamp) - Date.parse(limit.timestamp))
  if (!Number.isFinite(delta) || delta > 3_600_000) return null
  if (cpu.has(usage.unit) && cpu.has(limit.unit)) return usage.value / limit.value * 100
  return factors[usage.unit] && factors[limit.unit] ? usage.value * factors[usage.unit] / (limit.value * factors[limit.unit]) * 100 : null
}
