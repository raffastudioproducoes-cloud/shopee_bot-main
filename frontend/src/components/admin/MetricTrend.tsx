import { useId } from 'react'

export function trendGeometry(values: number[], timestamps?: string[]) {
  if (!values.length) return null
  const maximum = Math.max(1, ...values)
  const times = timestamps?.length === values.length ? timestamps.map(value => Date.parse(value)) : null
  const timeSpan = times ? times[times.length - 1] - times[0] : 0
  const points = values.map((value, index) => [40 + (times && timeSpan > 0 ? (times[index] - times[0]) / timeSpan : index / Math.max(1, values.length - 1)) * 440, 128 - value / maximum * 112])
  let line = `M${points[0].join(',')}`
  for (let index = 1; index < points.length; index++) {
    const [x, y] = points[index]
    const [previousX, previousY] = points[index - 1]
    const middle = (previousX + x) / 2
    // Controles dentro do intervalo preservam máximos e mínimos das amostras.
    line += ` C${middle},${previousY} ${middle},${y} ${x},${y}`
  }
  return { maximum, points, line, area: `${line} L${points[points.length - 1]![0]},128 L40,128 Z` }
}

export function MetricTrend({ values, timestamps, label, start, end, compact = false }: { values: number[]; timestamps?: string[]; label: string; start?: string; end?: string; compact?: boolean }) {
  const id = useId().replace(/:/g, '')
  const geometry = trendGeometry(values, timestamps)
  if (!geometry) return <p className="admin-muted">Sem amostras disponíveis.</p>
  return <svg className={`admin-trend${compact ? ' is-compact' : ''}`} viewBox="0 0 500 158" role="img" aria-label={label}>
    <defs><linearGradient id={`trend-${id}`} x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="var(--highlight)" stopOpacity=".24" /><stop offset="100%" stopColor="var(--highlight)" stopOpacity="0" /></linearGradient></defs>
    {[0, 1, 2, 3, 4].map(index => <line key={`v${index}`} x1={40 + index * 110} x2={40 + index * 110} y1="16" y2="128" className="admin-trend-grid" />)}
    {[0, 1, 2].map(index => <g key={index}><line x1="40" x2="480" y1={16 + index * 56} y2={16 + index * 56} className="admin-trend-grid" /><text x="32" y={20 + index * 56} textAnchor="end">{(geometry.maximum * (1 - index / 2)).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}</text></g>)}
    <path d={geometry.area} fill={`url(#trend-${id})`} />
    <path d={geometry.line} className="admin-trend-line" fill="none" pathLength="1" />
    {values.length === 1 && <circle cx={geometry.points[0][0]} cy={geometry.points[0][1]} r="3" fill="var(--highlight)" />}
    <text x="40" y="150">{start ?? (timestamps?.[0] ? new Date(timestamps[0]).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo' }) : '')}</text><text x="480" y="150" textAnchor="end">{end ?? (timestamps?.length ? new Date(timestamps[timestamps.length - 1]).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo' }) : '')}</text>
  </svg>
}

export function PlanRings({ values, total }: { values: number[]; total: number }) {
  return <svg className="admin-plan-rings" viewBox="0 0 150 150" role="img" aria-label={`Planos: Free ${values[0]}, Plus ${values[1]}, Premium ${values[2]}, em ${total} contas.`}>
    {values.map((value, index) => <g key={index}>
      <circle cx="75" cy="75" r={58 - index * 12} fill="none" stroke="var(--chart-grid)" strokeWidth="6" />
      <circle cx="75" cy="75" r={58 - index * 12} fill="none" stroke={`var(--chart-${index + 1})`} strokeWidth="6" pathLength="100" strokeDasharray={`${Math.min(100, value / Math.max(1, total) * 100)} 100`} transform="rotate(-90 75 75)" />
    </g>)}
    <text x="75" y="76" textAnchor="middle" className="admin-ring-total">{total}</text><text x="75" y="94" textAnchor="middle">contas</text>
  </svg>
}
