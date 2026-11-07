import { buildAdminDiagnosticSections } from './credentialPlatforms'

/** O backend de Análises só aceita estes cinco filtros operacionais. */
export const ANALYTICS_RECORDED_NETWORKS = ['facebook', 'instagram', 'threads', 'tiktok', 'x'] as const
export type AnalyticsRecordedNetwork = typeof ANALYTICS_RECORDED_NETWORKS[number]

type Coverage = { label: string; detail: string; tone: 'available' | 'limited' | 'planned' }

/** Cobertura efetiva, distinta da possibilidade futura indicada pelo catálogo de Credenciais. */
const COVERAGE: Readonly<Record<string, Coverage>> = {
  facebook: { label: 'Envios', detail: 'Histórico de envios; insights por publicação ainda sem coletor validado.', tone: 'limited' },
  instagram: { label: 'Envios', detail: 'Histórico de envios; insights por mídia dependem de integração e permissões.', tone: 'limited' },
  kwai: { label: 'Não integrado', detail: 'Não existe publicador nem coletor oficial habilitado no Auto Orbital.', tone: 'planned' },
  'shopee-video': { label: 'Aprovação pendente', detail: 'Shopee Video Management exige aprovação e OAuth específicos; não é Shopee Afiliados.', tone: 'planned' },
  telegram: { label: 'Em breve', detail: 'Integração com canais/bots ainda não implementada; métricas indisponíveis.', tone: 'planned' },
  threads: { label: 'Insights por post', detail: 'Coleta por ID de post confirmado, condicionada a OAuth e permissão de insights.', tone: 'available' },
  tiktok: { label: 'Envios', detail: 'Histórico de envios; insights de vídeos exigem integração e escopo video.list.', tone: 'limited' },
  whatsapp: { label: 'Em breve', detail: 'WhatsApp Business Cloud API e webhooks ainda não foram integrados.', tone: 'planned' },
  x: { label: 'Desabilitado', detail: 'Publicação bloqueada no produto; somente histórico de envios já registrado.', tone: 'limited' },
}

export const ANALYTICS_NETWORKS = buildAdminDiagnosticSections().social.map((platform) => ({
  ...platform,
  ...(COVERAGE[platform.key] ?? {
    label: 'Não integrado', detail: 'A coleta de métricas desta rede ainda não foi implementada.', tone: 'planned',
  }),
}))

export function hasRecordedAnalytics(network: string): network is AnalyticsRecordedNetwork {
  return (ANALYTICS_RECORDED_NETWORKS as readonly string[]).includes(network)
}
