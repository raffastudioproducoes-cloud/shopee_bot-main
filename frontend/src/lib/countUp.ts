/** Curva da contagem: começa devagar e acelera até o valor final (ease-in cúbico). */
export function countUpEase(progress: number): number {
  const p = Math.min(1, Math.max(0, Number.isFinite(progress) ? progress : 0))
  return p * p * p
}

/** Valor intermediário da contagem, sempre inteiro e limitado a [0, target]. */
export function countUpValue(target: number, progress: number): number {
  if (!Number.isFinite(target) || target <= 0) return Math.max(0, Math.trunc(target || 0))
  return Math.min(target, Math.round(target * countUpEase(progress)))
}
