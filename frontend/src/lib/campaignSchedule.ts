const MAX_CALENDAR_DAYS = 210
const TIME_ZONE = "America/Sao_Paulo"

function parseDateOnly(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) return null
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])))
  return date.toISOString().slice(0, 10) === value ? date : null
}

function addDays(date: Date, amount: number): Date {
  return new Date(date.getTime() + amount * 86_400_000)
}

function dateKey(date: Date): string {
  return date.toISOString().slice(0, 10)
}

function weekdayIndex(date: Date): number {
  return (date.getUTCDay() + 6) % 7
}

function selectedWeekdaySet(weekdays: number[]): Set<number> {
  return new Set(weekdays.filter((day) => Number.isInteger(day) && day >= 0 && day <= 6))
}

export function calendarDaysBetween(startDate: string, endDate: string): number {
  const start = parseDateOnly(startDate)
  const end = parseDateOnly(endDate)
  if (!start || !end || end < start) return 0
  return Math.floor((end.getTime() - start.getTime()) / 86_400_000) + 1
}

export function countSelectedWeekdays(startDate: string, endDate: string, weekdays: number[]): number {
  const start = parseDateOnly(startDate)
  const end = parseDateOnly(endDate)
  const selected = selectedWeekdaySet(weekdays)
  if (!start || !end || end < start || selected.size === 0) return 0
  let count = 0
  for (let offset = 0; offset < MAX_CALENDAR_DAYS; offset += 1) {
    const current = addDays(start, offset)
    if (current > end) break
    if (selected.has(weekdayIndex(current))) count += 1
  }
  return count
}

export function maxEndDateForSelectedWeekdays(
  startDate: string,
  weekdays: number[],
  activeDayLimit: number,
): string | undefined {
  const start = parseDateOnly(startDate)
  const selected = selectedWeekdaySet(weekdays)
  if (!start || selected.size === 0 || !Number.isInteger(activeDayLimit) || activeDayLimit < 1) {
    return undefined
  }
  let count = 0
  for (let offset = 0; offset < MAX_CALENDAR_DAYS; offset += 1) {
    const current = addDays(start, offset)
    if (selected.has(weekdayIndex(current))) {
      count += 1
      if (count === activeDayLimit) return dateKey(current)
    }
  }
  return undefined
}

function paidThroughLocal(value: string): { date: string; time: string } | null {
  const instant = new Date(value)
  if (!Number.isFinite(instant.getTime())) return null
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  }).formatToParts(instant)
  const part = (type: string) => parts.find((entry) => entry.type === type)?.value ?? ""
  return {
    date: `${part("year")}-${part("month")}-${part("day")}`,
    time: `${part("hour")}:${part("minute")}:${part("second")}`,
  }
}

function paidPeriodMaxDate(
  startDate: string,
  weekdays: number[],
  planMaxDate: string | undefined,
  lastPostingTime: string,
  paidThrough: string | null | undefined,
): string | undefined {
  if (!planMaxDate || !paidThrough) return planMaxDate
  const start = parseDateOnly(startDate)
  const paid = paidThroughLocal(paidThrough)
  const selected = selectedWeekdaySet(weekdays)
  if (!start || !paid || selected.size === 0) return planMaxDate
  const lastTime = /^\d{2}:\d{2}$/.test(lastPostingTime) ? `${lastPostingTime}:00` : lastPostingTime
  let lastAllowed: string | undefined
  for (let offset = 0; offset < MAX_CALENDAR_DAYS; offset += 1) {
    const current = addDays(start, offset)
    const key = dateKey(current)
    if (key > planMaxDate) break
    if (!selected.has(weekdayIndex(current))) continue
    if (key > paid.date || (key === paid.date && lastTime >= paid.time)) break
    lastAllowed = key
  }
  return lastAllowed
}

export interface CampaignScheduleUsage {
  calendarDays: number
  activeDaysUsed: number
  activeDaysRemaining: number
  planMaxEndDate?: string
  maxEndDate?: string
  lastPostingTime: string
  exceedsActiveDayLimit: boolean
  exceedsCalendarLimit: boolean
  paidPeriodShortensWindow: boolean
  paidPeriodHasNoEligibleDay: boolean
}

export function calculateCampaignScheduleUsage(args: {
  startDate: string
  endDate: string
  weekdays: number[]
  activeDayLimit: number
  startTime: string
  endTime: string
  postsPerDay: number
  paidThrough?: string | null
}): CampaignScheduleUsage {
  const calendarDays = calendarDaysBetween(args.startDate, args.endDate)
  const activeDaysUsed = countSelectedWeekdays(args.startDate, args.endDate, args.weekdays)
  const lastPostingTime = args.postsPerDay > 1 ? args.endTime : args.startTime
  const planMaxEndDate = maxEndDateForSelectedWeekdays(
    args.startDate, args.weekdays, args.activeDayLimit,
  )
  const paidMaxEndDate = paidPeriodMaxDate(
    args.startDate, args.weekdays, planMaxEndDate, lastPostingTime, args.paidThrough,
  )
  const paidPeriodHasNoEligibleDay = Boolean(args.paidThrough && planMaxEndDate && !paidMaxEndDate)
  const maxEndDate = paidMaxEndDate ?? planMaxEndDate
  return {
    calendarDays,
    activeDaysUsed,
    activeDaysRemaining: Math.max(0, args.activeDayLimit - activeDaysUsed),
    planMaxEndDate,
    maxEndDate,
    lastPostingTime,
    exceedsActiveDayLimit: activeDaysUsed > args.activeDayLimit,
    exceedsCalendarLimit: calendarDays > MAX_CALENDAR_DAYS,
    paidPeriodShortensWindow: Boolean(paidMaxEndDate && planMaxEndDate && paidMaxEndDate < planMaxEndDate),
    paidPeriodHasNoEligibleDay,
  }
}

export function formatCampaignDate(value: string): string {
  const date = parseDateOnly(value)
  return date ? date.toLocaleDateString("pt-BR", { timeZone: "UTC" }) : value
}
