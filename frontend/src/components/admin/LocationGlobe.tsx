import { useEffect, useId, useMemo, useRef, useState } from 'react'
import type { AdminMetrics } from '../../api/adminMetrics'
import { Panel } from '../ui/Panel'
import { Button } from '../ui/Button'
import { clampZoom, earthRotation, projectGlobe, wheelGlobeZoom } from './globeGeometry'
import { formatMetricTime, isStale } from './metricsPresentation'
import { CardTags } from './CardTags'
import land from './globeLand.json'

const places: Record<string, { name: string; longitude: number; latitude: number; country: string }> = {
  BR: { name: 'Brasil', longitude: -52, latitude: -14, country: 'BR' },
  'BR-RJ': { name: 'Rio de Janeiro · RJ', longitude: -42.5, latitude: -22, country: 'BR' },
  'BR-SP': { name: 'São Paulo · SP', longitude: -48.5, latitude: -22.5, country: 'BR' },
  'BR-MG': { name: 'Minas Gerais · MG', longitude: -44.5, latitude: -18.5, country: 'BR' },
  'BR-BA': { name: 'Bahia · BA', longitude: -41.5, latitude: -12, country: 'BR' },
  PT: { name: 'Portugal', longitude: -8, latitude: 39.5, country: 'PT' },
  US: { name: 'Estados Unidos', longitude: -98, latitude: 38, country: 'US' },
  GB: { name: 'Reino Unido', longitude: -2, latitude: 54, country: 'GB' },
  DE: { name: 'Alemanha', longitude: 10, latitude: 51, country: 'DE' },
  JP: { name: 'Japão', longitude: 138, latitude: 37, country: 'JP' },
  AU: { name: 'Austrália', longitude: 134, latitude: -25, country: 'AU' },
}
const demoRegions = [
  { region: 'BR-RJ', online: 18, offline: 42, deleted: 5 },
  { region: 'BR-SP', online: 32, offline: 86, deleted: 8 },
  { region: 'BR-MG', online: 9, offline: 27, deleted: 2 },
  { region: 'BR-BA', online: 6, offline: 14, deleted: 1 },
  { region: 'PT', online: 8, offline: 19, deleted: 2 },
  { region: 'US', online: 14, offline: 33, deleted: 3 },
  { region: 'JP', online: 5, offline: 12, deleted: 1 },
  { region: 'AU', online: 3, offline: 7, deleted: 1 },
]
const states = [['online', 'Atividade recente'], ['offline', 'Sem atividade recente'], ['deleted', 'Contas excluídas']] as const

export function LocationGlobe({ data }: { data: AdminMetrics }) {
  const id = useId().replace(/:/g, '')
  const [demo, setDemo] = useState(false)
  const [center, setCenter] = useState({ longitude: -45, latitude: -12 })
  const [zoom, setZoom] = useState(1)
  const [country, setCountry] = useState('all')
  const [selected, setSelected] = useState<string | null>(null)
  const [rotating, setRotating] = useState(true)
  const [hovered, setHovered] = useState(false)
  const [focusWithin, setFocusWithin] = useState(false)
  const [reducedMotion, setReducedMotion] = useState(false)
  const svgRef = useRef<SVGSVGElement>(null)
  const inView = useRef(true)
  const drag = useRef<{ x: number; y: number; longitude: number; latitude: number } | null>(null)
  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)')
    const change = () => setReducedMotion(media.matches)
    change(); media.addEventListener('change', change)
    const observer = new IntersectionObserver(entries => { inView.current = entries[0]?.isIntersecting ?? false })
    if (svgRef.current) observer.observe(svgRef.current)
    return () => { media.removeEventListener('change', change); observer.disconnect() }
  }, [])
  useEffect(() => {
    const svg = svgRef.current
    if (!svg) return
    const wheel = (event: WheelEvent) => {
      if (event.ctrlKey) return
      event.preventDefault()
      setZoom(current => wheelGlobeZoom(current, event.deltaY, event.deltaMode))
    }
    svg.addEventListener('wheel', wheel, { passive: false })
    return () => svg.removeEventListener('wheel', wheel)
  }, [])
  useEffect(() => {
    if (!rotating || hovered || focusWithin || reducedMotion || zoom > 1) return
    let frame = 0
    let previous = 0
    const tick = (now: number) => {
      if (!previous || document.hidden || !inView.current) previous = now
      if (now - previous >= 33) {
        const elapsed = now - previous; previous = now
        setCenter(current => ({ ...current, longitude: earthRotation(current.longitude, elapsed) }))
      }
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [rotating, hovered, focusWithin, reducedMotion, zoom])
  const source = demo ? demoRegions : data.geography?.status === 'available' ? data.geography.regions : []
  const mapped = source.filter(row => places[row.region])
  const regions = mapped.filter(row => country === 'all' || places[row.region].country === country)
  const selectedRegion = regions.find(row => row.region === selected)
  const totals = regions.reduce((sum, row) => ({ online: sum.online + row.online, offline: sum.offline + row.offline, deleted: sum.deleted + row.deleted }), { online: 0, offline: 0, deleted: 0 })
  const hasData = demo || data.geography?.status === 'available'
  const projection = (longitude: number, latitude: number) => projectGlobe(longitude, latitude, center.longitude, center.latitude, zoom, 23.44)
  const dots = useMemo(() => land.map(([lon, lat]) => projectGlobe(lon, lat, center.longitude, center.latitude, zoom, 23.44)).filter(point => point.visible).map(point => `M${point.x.toFixed(1)},${point.y.toFixed(1)}h.01`).join(''), [center, zoom])
  const grid = useMemo(() => {
    const lines: string[] = []
    for (let latitude = -60; latitude <= 60; latitude += 30) {
      let path = ''; let visible = false
      for (let longitude = -180; longitude <= 180; longitude += 4) {
        const point = projectGlobe(longitude, latitude, center.longitude, center.latitude, zoom, 23.44)
        if (point.visible) path += `${visible ? 'L' : 'M'}${point.x.toFixed(1)},${point.y.toFixed(1)}`
        visible = point.visible
      }
      lines.push(path)
    }
    for (let longitude = -180; longitude < 180; longitude += 30) {
      let path = ''; let visible = false
      for (let latitude = -90; latitude <= 90; latitude += 4) {
        const point = projectGlobe(longitude, latitude, center.longitude, center.latitude, zoom, 23.44)
        if (point.visible) path += `${visible ? 'L' : 'M'}${point.x.toFixed(1)},${point.y.toFixed(1)}`
        visible = point.visible
      }
      lines.push(path)
    }
    return lines.join('')
  }, [center, zoom])
  function focus(region: string) {
    const place = places[region]
    if (!place) return
    setSelected(region)
    setCenter({ longitude: place.longitude, latitude: place.latitude })
    setZoom(region.includes('-') ? 3 : 1.8)
  }
  function chooseCountry(code: string) {
    setCountry(code); setSelected(null)
    if (code === 'all') { setCenter({ longitude: -45, latitude: -12 }); setZoom(1) }
    else { const place = places[code]; if (place) { setCenter({ longitude: place.longitude, latitude: place.latitude }); setZoom(1.8) } }
  }
  return <Panel surface="dark" className="admin-globe-panel">
    <div className="admin-globe-heading"><div><CardTags tags={demo ? ['app', 'demo'] : hasData ? ['clients', 'geography'] : ['app', 'no_data']} /><span className="admin-globe-eyebrow">PRESENÇA GLOBAL</span><h2>Onde estão seus clientes</h2><p>Explore países e regiões · localização aproximada</p></div><Button variant="ghost" aria-pressed={demo} onClick={() => { setDemo(!demo); setSelected(null); chooseCountry('all') }}>{demo ? 'Voltar aos dados reais' : 'Explorar demonstração'}</Button></div>
    <div className="admin-globe-status" role="status">{demo ? 'DEMONSTRAÇÃO · todos os pontos e números são fictícios' : hasData ? `Coleta: ${data.geography?.updated_at ? formatMetricTime(data.geography.updated_at) : 'horário indisponível'}${data.geography?.updated_at && isStale(data.geography.updated_at) ? ' · Dados antigos' : ''}` : 'Em breve · Localização ainda não coletada. Nenhum ponto real é exibido.'}</div>
    <div className="admin-globe-layout">
      <div className="admin-globe-scene" onPointerEnter={() => setHovered(true)} onPointerLeave={() => setHovered(false)} onFocusCapture={() => setFocusWithin(true)} onBlurCapture={event => { if (!event.currentTarget.contains(event.relatedTarget)) setFocusWithin(false) }}>
        <svg ref={svgRef} className="admin-globe" viewBox="0 0 640 500" role="group" aria-label="Globo interativo: arraste para girar; setas para rotação; roda do mouse ou botões para zoom" tabIndex={0}
          onKeyDown={event => {
            const movements: Record<string, [number, number]> = { ArrowLeft: [-8, 0], ArrowRight: [8, 0], ArrowUp: [0, 8], ArrowDown: [0, -8] }
            if (movements[event.key]) { event.preventDefault(); const [lon, lat] = movements[event.key]; setCenter(current => ({ longitude: current.longitude + lon, latitude: Math.max(-80, Math.min(80, current.latitude + lat)) })) }
            else if (event.key === '+' || event.key === '=') { event.preventDefault(); setZoom(current => clampZoom(current + .2)) }
            else if (event.key === '-') { event.preventDefault(); setZoom(current => clampZoom(current - .2)) }
          }}
          onPointerDown={event => { if (event.pointerType !== 'mouse' || event.button === 0) { drag.current = { x: event.clientX, y: event.clientY, ...center }; event.currentTarget.setPointerCapture(event.pointerId) } }}
          onPointerMove={event => { if (drag.current) { const initial = drag.current; setCenter({ longitude: initial.longitude - (event.clientX - initial.x) * .35 / zoom, latitude: Math.max(-80, Math.min(80, initial.latitude + (event.clientY - initial.y) * .35 / zoom)) }) } }}
          onPointerUp={() => { drag.current = null }} onPointerCancel={() => { drag.current = null }} onLostPointerCapture={() => { drag.current = null }}>
          <defs><radialGradient id={`ocean-${id}`} cx="35%" cy="30%"><stop offset="0%" stopColor="var(--surface-card)" /><stop offset="100%" stopColor="var(--graphite-950)" /></radialGradient><radialGradient id={`atmosphere-${id}`}><stop offset="88%" stopColor="var(--highlight)" stopOpacity="0" /><stop offset="97%" stopColor="var(--highlight)" stopOpacity=".12" /><stop offset="100%" stopColor="var(--highlight)" stopOpacity="0" /></radialGradient><clipPath id={`sphere-${id}`}><circle cx="320" cy="250" r={200 * zoom} /></clipPath></defs>
          <ellipse cx="320" cy="250" rx="245" ry="90" transform="rotate(-24 320 250)" className="admin-globe-orbit" />
          <circle cx="320" cy="250" r={215 * zoom} fill={`url(#atmosphere-${id})`} />
          <circle cx="320" cy="250" r={200 * zoom} fill={`url(#ocean-${id})`} className="admin-globe-rim" />
          <g clipPath={`url(#sphere-${id})`}><path d={grid} className="admin-globe-grid" /><path d={dots} className="admin-globe-land" />
            {regions.map(row => { const place = places[row.region]; const point = projection(place.longitude, place.latitude); if (!point.visible) return null; return <g key={row.region} role="button" tabIndex={0} aria-label={`${place.name}: ${row.online} com atividade recente, ${row.offline} sem atividade recente, ${row.deleted} excluídas. Selecionar região.`} className={`admin-globe-point${selected === row.region ? ' is-selected' : ''}`} onPointerDown={event => event.stopPropagation()} onClick={() => focus(row.region)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); event.stopPropagation(); focus(row.region) } }}>
              <title>{place.name}</title><circle cx={point.x} cy={point.y} r="19" fill="transparent" />
              {states.map(([state], index) => row[state] > 0 && <circle key={state} cx={point.x + (index - 1) * 10} cy={point.y} r={Math.min(7, 2.5 + Math.log10(row[state] + 1))} className={`admin-globe-light is-${state}`} />)}
              {zoom > 1.3 && selected === row.region && <text x={point.x} y={point.y - 17} textAnchor="middle">{place.name}</text>}
            </g> })}
          </g>
        </svg>
        <div className="admin-globe-controls"><Button variant="secondary" aria-label="Diminuir zoom do globo" disabled={zoom <= 1} onClick={() => setZoom(current => clampZoom(current - .25))}>−</Button><output aria-label="Nível de zoom">{zoom.toFixed(2)}×</output><Button variant="secondary" aria-label="Aumentar zoom do globo" disabled={zoom >= 3} onClick={() => setZoom(current => clampZoom(current + .25))}>+</Button><Button variant="ghost" onClick={() => chooseCountry('all')}>Recentrar</Button><Button variant="ghost" disabled={reducedMotion} aria-pressed={rotating && !reducedMotion} onClick={() => setRotating(!rotating)}>{rotating && !reducedMotion ? 'Pausar rotação' : 'Girar'}</Button></div>
        <p className="admin-globe-help">Arraste para girar · roda do mouse para zoom · eixo inclinado 23,44°</p>
      </div>
      <div className="admin-globe-detail"><label htmlFor={`globe-country-${id}`}>Explorar região</label><select id={`globe-country-${id}`} value={country} onChange={event => chooseCountry(event.target.value)}><option value="all">Mundo</option>{['BR', 'PT', 'US', 'GB', 'DE', 'JP', 'AU'].map(code => <option value={code} key={code}>{places[code].name}</option>)}</select>
        <h3>{selectedRegion ? places[selectedRegion.region].name : country === 'all' ? 'Visão global' : places[country].name}</h3>
        <dl className="admin-globe-counts">{states.map(([state, label]) => <div key={state}><dt><i className={`admin-globe-legend is-${state}`} />{label}</dt><dd>{hasData ? (selectedRegion ?? totals)[state].toLocaleString('pt-BR') : '—'}</dd></div>)}</dl>
        <p>Contas atuais: {hasData ? ((selectedRegion ?? totals).online + (selectedRegion ?? totals).offline).toLocaleString('pt-BR') : '—'}. Excluídas são um agregado histórico separado.</p>
        {regions.length > 0 && <div className="admin-globe-regions" aria-label="Regiões disponíveis">{regions.map(row => <button type="button" key={row.region} aria-pressed={selected === row.region} onClick={() => focus(row.region)}><span>{places[row.region].name}</span><strong>{(row.online + row.offline).toLocaleString('pt-BR')}</strong></button>)}</div>}
        {source.length > mapped.length && <p>Há regiões sem representação cartográfica nesta versão.</p>}
        <p className="admin-globe-privacy">Um ponto representa uma região, nunca uma pessoa. Luz acesa: atividade recente; apagada: sem atividade recente, não confirmação de logout. Vermelha: exclusões agregadas. Não há endereço, GPS ou IP neste mapa.</p>
      </div>
    </div>
    <details className="admin-globe-method"><summary>Como os pontos serão contabilizados</summary><p>Localização aproximada declarada ou fonte autorizada, agregada por país/UF. Presença requer sinal recente com expiração; logout e exclusão precisam de eventos próprios. Contas sem região conhecida ficam fora dos pontos. Histórico de exclusões preserva apenas contagens por região e período. Dados reais ainda não estão integrados.</p><p>Base cartográfica: <a href="https://www.naturalearthdata.com/about/terms-of-use/" target="_blank" rel="noreferrer">Natural Earth · domínio público</a>.</p></details>
  </Panel>
}
