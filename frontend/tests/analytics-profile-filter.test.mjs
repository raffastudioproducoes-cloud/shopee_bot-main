import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const page = readFileSync(new URL('../src/pages/AnalyticsPage.tsx', import.meta.url), 'utf8')

test('o seletor começa em Todos e lista somente perfis retornados pela conta', () => {
  assert.match(page, /useState\('all'\)/)
  assert.match(page, /<Select label="Perfil" value=\{selectedProfile\}/)
  assert.match(page, /value: 'all', label: 'Todos os perfis'/)
  assert.match(page, /\.\.\.\(profiles \?\? \[\]\)\.map/)
  assert.match(page, /queryFn: profilesApi\.list/)
})

test('a consulta troca somente o escopo visual e mantém cache isolado', () => {
  assert.match(page, /queryKey: \['analytics-summary', userId, selectedProfile, days, network\]/)
  assert.match(page, /queryKey: \['analytics-timeline', userId, selectedProfile, days, network\]/)
  assert.match(page, /selectedProfileQuery = `&profile_id=/)
  assert.doesNotMatch(page, /setActiveProfileId\s*\(/)
  assert.doesNotMatch(page, /profilesApi\.activate\s*\(/)
  assert.match(page, /formDraftKey\(userId, 'analytics-filters', profileId\)/)
})

test('atualização manual aceita Todos, respeita cota diária e ranking por post segue a seleção', () => {
  assert.match(page, /queryKey: \['analytics-refresh-quota', userId\]/)
  assert.match(page, /\/analytics\/refresh\/quota/)
  assert.match(page, /quotaReached = !refreshQuota\?\.unlimited && refreshQuota\?\.remaining === 0/)
  assert.match(page, /disabled=\{refreshing \|\| quotaLoading \|\| quotaError \|\| !refreshQuota \|\| quotaReached/)
  assert.match(page, /ADMIN: atualizações ilimitadas/)
  assert.match(page, /atualizações restantes hoje/)
  assert.match(page, /disabled=\{probing !== null \|\| selectedProfile === 'all'\}/)
  assert.match(page, /\/analytics\/refresh\?profile_id=/)
  assert.match(page, /\/analytics\/probe\/\$\{name\}\?profile_id=/)
  assert.match(page, /queryKey: \['analytics-posts', userId, selectedProfile, days, network\]/)
  assert.match(page, /<AnalyticsVisuals rows=\{rows\}/)
  assert.doesNotMatch(page, /page_media_view|Visualizações da Página do Facebook/)
  assert.match(page, /Nunca usamos visualizações gerais do perfil ou da Página/)
})

test('o dashboard apresenta métricas por post, redes sociais completas e visualizações distintas', () => {
  const visuals = readFileSync(new URL('../src/components/AnalyticsVisuals.tsx', import.meta.url), 'utf8')
  assert.match(visuals, /buildAdminDiagnosticSections\(\)\.social/)
  assert.match(page, /ANALYTICS_NETWORKS\.map\(\(item\) => \(\{ value: item\.key, label: item\.title \}\)\)/)
  assert.doesNotMatch(page, /AnalyticsDetailTable|Detalhamento por rede|Desempenho por publicação|analytics-performance-table/)
  assert.match(page, /hasRecordedAnalytics\(network\)/)
  assert.match(page, /análises indisponíveis/)
  for (const widget of ['Total de envios', 'Redes com atividade', 'Visualizações de posts',
    'Interações mensuradas', 'Posts com insights', 'Comparação entre redes',
    'Composição do engajamento', 'Atividade por dia da semana', 'Publicações em destaque',
    'Situação das nove redes']) assert.ok(visuals.includes(widget), `ausente: ${widget}`)
  assert.match(visuals, /item\.value === null \? '—'/)
  assert.doesNotMatch(visuals, /Visualizações da Página/)
})

test('tabelas redundantes removidas sem perder métricas oficiais e rastreabilidade nos cards', () => {
  const visuals = readFileSync(new URL('../src/components/AnalyticsVisuals.tsx', import.meta.url), 'utf8')
  const styles = readFileSync(new URL('../src/styles/analytics-panels.css', import.meta.url), 'utf8')
  assert.doesNotMatch(page, /<table|analytics-desktop-table|analytics-mobile-list/)
  assert.match(visuals, /analytics-social-metrics/)
  assert.match(visuals, /\['Visualizações', row\.views\]/)
  assert.match(visuals, /\['Curtidas', row\.likes\]/)
  assert.match(visuals, /\['Comentários', row\.comments\]/)
  assert.match(visuals, /\['Reposts', row\.reposts\]/)
  assert.match(visuals, /\['Cliques', row\.clicks\]/)
  assert.match(visuals, /post\.finished_at/)
  assert.match(visuals, /collectionLabel\(post\.state\)/)
  assert.match(visuals, /post\.views === null \? '—'/)
  assert.match(visuals, /analytics-post-metrics/)
  assert.match(styles, /\.analytics-post-metrics/)
  assert.match(styles, /\.analytics-social-metrics/)
  assert.match(page, /Traço significa métrica indisponível, não zero/)
})
