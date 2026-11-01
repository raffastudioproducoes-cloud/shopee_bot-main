import type { Post, PostScheduleEntry } from "../../api/posts"
import { formatUtcTimestampBrasilia, isoToBr } from "../../lib/ptBrDateTime"
import { NETWORK_RULES } from "../../lib/networkLimits"

export const WEEKDAY_NAMES = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

export function postKind(post: Post): "Imediato" | "Agendado" | "Recorrente" {
  if (post.publish_immediately === true) return "Imediato"
  if (post.schedule_trigger === "cron" || post.schedule_entries?.some((entry) => entry.trigger === "cron")) return "Recorrente"
  if (post.schedule_trigger === "date" || post.schedule_entries?.some((entry) => entry.trigger === "date")) return "Agendado"
  return post.scheduled ? "Agendado" : "Imediato"
}

function scheduleDays(entry: PostScheduleEntry): string[] {
  const days = entry.days_of_week?.length ? entry.days_of_week : entry.day_of_week != null ? [entry.day_of_week] : []
  return [...new Set(days)].sort((a, b) => a - b).map((day) => WEEKDAY_NAMES[day]).filter((day): day is string => Boolean(day))
}

export function scheduleLines(post: Post): string[] {
  if (post.publish_immediately === true) return []
  const entries = post.schedule_entries ?? []
  const dates = [...new Set(entries.filter((entry) => entry.trigger === "date" && entry.run_date).map((entry) => formatUtcTimestampBrasilia(entry.run_date!)))]
  const cronEntries = entries.filter((entry) => entry.trigger === "cron")
  const grouped = new Map<string, Set<string>>()
  for (const entry of cronEntries) {
    const days = scheduleDays(entry)
    const clock = entry.time?.slice(0, 5)
    for (const day of days) {
      if (!grouped.has(day)) grouped.set(day, new Set())
      if (clock) grouped.get(day)!.add(clock)
    }
  }
  const recurring = WEEKDAY_NAMES.filter((day) => grouped.has(day)).map((day) => {
    const times = [...grouped.get(day)!].sort()
    return day + ": " + (times.length ? times.join(", ") : "horário não informado")
  })
  const startDates = [...new Set(cronEntries.map((entry) => entry.start_date?.slice(0, 10)).filter((date): date is string => Boolean(date)))]
  const starts = startDates.map((date) => "Início: " + isoToBr(date))
  if (dates.length || recurring.length) return [...dates.map((date) => "Programado: " + date), ...starts, ...recurring]
  if (post.scheduled_for && post.schedule_trigger === "date") return ["Programado: " + formatUtcTimestampBrasilia(post.scheduled_for)]
  if (post.schedule_trigger === "cron") return ["Recorrência cadastrada; detalhes indisponíveis no momento."]
  return []
}

/** Um agendamento cron preservado significa que há novas ocorrências previstas,
 * mesmo quando a última publicação já foi concluída. */
export function recurringInProgress(post: Post): boolean {
  return post.scheduled && postKind(post) === "Recorrente"
}

/** Cards usam somente um resumo; o mapeamento completo permanece no modal. */
export function compactScheduleSummary(post: Post): string | null {
  if (postKind(post) === "Imediato") return null
  if (postKind(post) === "Agendado") {
    const date = post.schedule_entries?.find((entry) => entry.trigger === "date")?.run_date ?? post.scheduled_for
    return date ? "Programado: " + formatUtcTimestampBrasilia(date).replace(/:\d{2}$/, "") : "Agendamento registrado"
  }

  const recurring = (post.schedule_entries ?? []).filter((entry) => entry.trigger === "cron")
  const days = new Set<number>()
  const times = new Set<string>()
  for (const entry of recurring) {
    const entryDays = entry.days_of_week?.length ? entry.days_of_week : entry.day_of_week != null ? [entry.day_of_week] : []
    for (const day of entryDays) days.add(day)
    if (entry.time) times.add(entry.time.slice(0, 5))
  }
  const daysLabel = days.size === 7 ? "Todos os dias" : days.size ? days.size + (days.size === 1 ? " dia" : " dias") : "Recorrência"
  const orderedTimes = [...times].sort()
  const visibleTimes = orderedTimes.slice(0, 3).join(", ")
  const timesLabel = visibleTimes
    ? visibleTimes + (orderedTimes.length > 3 ? " +" + (orderedTimes.length - 3) : "")
    : "horários no detalhe"
  return daysLabel + " · " + timesLabel
}

export function lastPublishedLabel(post: Post): string | null {
  if (!post.last_result?.at) return null
  return formatUtcTimestampBrasilia(post.last_result.at)
}

export function postSearchText(post: Post): string {
  const dates = [post.created_at, post.updated_at, post.scheduled_for, post.last_result?.at]
    .filter((value): value is string => Boolean(value))
    .flatMap((value) => [value, formatUtcTimestampBrasilia(value)])
  const runDates = (post.schedule_entries ?? []).flatMap((entry) => {
    if (!entry.run_date) return []
    return [entry.run_date, formatUtcTimestampBrasilia(entry.run_date)]
  })
  const startDates = (post.schedule_entries ?? []).map((entry) => entry.start_date ? isoToBr(entry.start_date.slice(0, 10)) : "")
  const clockTimes = (post.schedule_entries ?? []).map((entry) => entry.time ?? "")
  return [post.text, ...post.texts, ...post.products.flatMap((product) => [product.name, product.product_id]), NETWORK_RULES[post.network ?? "threads"].label, post.network ?? "threads", postKind(post), ...scheduleLines(post), ...dates, ...runDates, ...startDates, ...clockTimes, post.last_result?.status ?? "", post.last_result?.error ?? ""].join(" ").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR")
}

export function matchesPost(post: Post, query: string): boolean {
  const normalized = query.trim().normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR")
  return !normalized || postSearchText(post).includes(normalized)
}
