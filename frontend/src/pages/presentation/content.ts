// Conteúdo textual da apresentação Auto Orbital (copiado fielmente da página original).
// Limites dos planos: migração 072 (plan_limits) e decisão de produto F4 de 03/11/2026.

export const LOGIN_PATH = "/login"

export const orbitSteps = ["Descobrir", "Preparar", "Planejar", "Acompanhar"] as const

export interface NetworkTask {
  name: string
  action: string
}

export const networks: NetworkTask[] = [
  { name: "Facebook", action: "Adaptar e publicar" },
  { name: "Instagram", action: "Revisar e enviar" },
  { name: "Threads", action: "Adaptar e publicar" },
  { name: "TikTok", action: "Revisar e enviar" },
  { name: "X", action: "Adaptar e publicar" },
]

export const weekDays = ["SEG", "TER", "QUA", "QUI", "SEX"] as const

export const routineTasks = [
  { label: "Revisar publicações pendentes", when: "Hoje" },
  { label: "Adaptar novos conteúdos", when: "Próximo" },
  { label: "Conferir destinos", when: "Depois" },
]

export const flowSteps = ["Produto", "Conteúdo", "Agenda", "Acompanhamento"] as const

export interface ProductStep {
  number: string
  title: string
  subtitle: string
  description: string
}

export const productSteps: ProductStep[] = [
  { number: "01", title: "Produtos", subtitle: "Encontre a oportunidade", description: "Pesquise e selecione produtos de uma loja integrada." },
  { number: "02", title: "Listas", subtitle: "Organize suas escolhas", description: "Agrupe produtos em listas para continuar de onde parou." },
  { number: "03", title: "Editor", subtitle: "Prepare o conteúdo", description: "Reúna a preparação de textos, com apoio de IA configurada." },
  { number: "04", title: "Agendamento", subtitle: "Defina o momento", description: "Planeje horários conforme a rede e a autorização." },
  { number: "05", title: "Histórico", subtitle: "Acompanhe a execução", description: "Acompanhe o que foi publicado e o que está por vir." },
]

export const benefits = [
  { number: "01", title: "Organização para continuar de onde parou.", text: "Produtos e listas evitam que cada nova publicação comece com uma busca do zero.", tag: "Recurso existente" },
  { number: "02", title: "Mais apoio na hora de encontrar as palavras.", text: "O editor reúne a preparação de textos e pode contar com assistência de IA configurada.", tag: "IA depende de configuração" },
  { number: "03", title: "Mais intenção, menos improviso.", text: "Planeje horários e acompanhe publicações sem depender apenas da memória.", tag: "Conforme rede e autorização" },
]

export const faq = [
  { q: "Preciso publicar manualmente em cada rede?", a: "O Auto Orbital reúne a preparação e o agendamento em um fluxo centralizado. A publicação depende das redes conectadas, do formato de cada conteúdo e das autorizações concedidas por cada plataforma." },
  { q: "Funciona com qualquer programa de afiliados?", a: "A Shopee é a primeira integração de catálogo. A expansão para outros programas está em estudo e depende de APIs, permissões e viabilidade técnica. O Auto Orbital não promete compatibilidade universal neste momento." },
  { q: "Minha rede social fica protegida?", a: "A conexão das redes compatíveis usa os mecanismos de autorização oferecidos pelos provedores. Cada integração pode solicitar permissões específicas, e a disponibilidade depende da aprovação e das regras de cada rede." },
  { q: "A inteligência artificial já faz tudo sozinha?", a: "Hoje existem recursos de assistência à criação de textos sujeitos à configuração. A coleta, seleção, criação e publicação totalmente autônomas fazem parte da visão em desenvolvimento, ainda não disponível." },
  { q: "Já posso contratar um plano?", a: "Ainda não. Os planos Free, Pro e Premium e seus limites já estão definidos, e os valores de referência aparecem na seção Valores. A contratação só abre no início da comercialização." },
]

/** Converte o progresso do scroll (0–1) no índice de etapa ativa, limitado ao total. */
export function progressToStep(progress: number, total: number): number {
  if (total <= 0) return 0
  const clamped = Math.min(Math.max(progress, 0), 1)
  return Math.min(total - 1, Math.floor(clamped * total))
}

/* ---------- Planos ---------- */

export type PlanId = "free" | "pro" | "premium"

export interface PlanInfo {
  id: PlanId
  name: string
  tagline: string
  /** Produtos salvos no catálogo (compartilhado pela conta). */
  products: number
  /** Listas por perfil. */
  lists: number
  /** Perfis no total (principal + secundários). */
  profiles: number
  /** Postagens por hora em "Enviar agora" (cada rede conta 1). */
  postsPerHour: number
  /** Horários de postagem por dia no recorrente. */
  recurringSlots: number
  /** Campanhas: null = sem acesso. */
  campaign: { maxDays: number; postsPerDay: number; active: number } | null
  automation: boolean
}

export const plans: PlanInfo[] = [
  { id: "free", name: "Free", tagline: "Para conhecer a órbita", products: 100, lists: 20, profiles: 1, postsPerHour: 1, recurringSlots: 1, campaign: null, automation: false },
  { id: "pro", name: "Pro", tagline: "Para ganhar ritmo", products: 500, lists: 20, profiles: 3, postsPerHour: 3, recurringSlots: 5, campaign: { maxDays: 15, postsPerDay: 3, active: 2 }, automation: false },
  { id: "premium", name: "Premium", tagline: "Para operar em escala", products: 2000, lists: 100, profiles: 5, postsPerHour: 5, recurringSlots: 5, campaign: { maxDays: 30, postsPerDay: 15, active: 5 }, automation: true },
]

/* ---------- Oferta ---------- */

export interface PlanOffer {
  id: PlanId
  /** Preço exibido. Pro e Premium: valores de referência informados por Rafa em 09/11/2026 (mensal). */
  priceLabel: string
  priceNote: string
  highlight: boolean
}

export const planOffers: PlanOffer[] = [
  { id: "free", priceLabel: "Grátis", priceNote: "Para começar sem custo", highlight: false },
  { id: "pro", priceLabel: "R$ 59,90", priceNote: "por mês · valor de referência", highlight: true },
  { id: "premium", priceLabel: "R$ 109,90", priceNote: "por mês · valor de referência", highlight: false },
]

export type ComparisonValue = string | boolean

export interface ComparisonRow {
  label: string
  values: Record<PlanId, ComparisonValue>
}

/** Formata números no padrão brasileiro (2.000). */
export function formatCount(value: number): string {
  return Math.round(value).toLocaleString("pt-BR")
}

/** Linhas da tabela comparativa, derivadas dos limites oficiais. */
export function buildComparison(list: PlanInfo[] = plans): ComparisonRow[] {
  const pick = (fn: (plan: PlanInfo) => ComparisonValue): Record<PlanId, ComparisonValue> =>
    Object.fromEntries(list.map((plan) => [plan.id, fn(plan)])) as Record<PlanId, ComparisonValue>
  return [
    { label: "Produtos no catálogo", values: pick((p) => formatCount(p.products)) },
    { label: "Listas por perfil", values: pick((p) => formatCount(p.lists)) },
    { label: "Perfis", values: pick((p) => String(p.profiles)) },
    { label: "Enviar agora (por hora)", values: pick((p) => String(p.postsPerHour)) },
    { label: "Horários recorrentes/dia", values: pick((p) => String(p.recurringSlots)) },
    { label: "Campanhas", values: pick((p) => (p.campaign ? `${p.campaign.maxDays} dias · ${p.campaign.postsPerDay}/dia · ${p.campaign.active} ativas` : false)) },
    { label: "Automação", values: pick((p) => p.automation) },
  ]
}
