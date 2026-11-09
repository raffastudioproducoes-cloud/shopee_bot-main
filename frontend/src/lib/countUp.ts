/** Valor intermediário da contagem: easeOutCubic, sempre inteiro e limitado a [0, target]. */
export function countUpValue(target: number, progress: number): number {
  if (!Number.isFinite(target) || target <= 0) return Math.max(0, Math.trunc(target || 0))
  const p = Math.min(1, Math.max(0, progress))
  const eased = 1 - Math.pow(1 - p, 3)
  return Math.min(target, Math.round(target * eased))
}
