// Filtro de status da página Posts. Espelha _STATUS_GROUP de api/routers/posts.py:
// o servidor filtra a lista; aqui só contamos o que já foi carregado e lemos a URL.

export type PostStatusFilter =
  | "all" | "attention" | "unknown" | "failed" | "running" | "pending" | "published" | "manual"

type StatusGroup = Exclude<PostStatusFilter, "all" | "attention">

export const STATUS_FILTERS: { key: PostStatusFilter; label: string }[] = [
  { key: "all", label: "Todos" },
  { key: "attention", label: "Precisam de atenção" },
  { key: "unknown", label: "Sem confirmação" },
  { key: "failed", label: "Falhou" },
  { key: "running", label: "Em execução" },
  { key: "pending", label: "Agendado / pendente" },
  { key: "published", label: "Publicado" },
  { key: "manual", label: "Confirmado por você" },
]

const GROUP_BY_STATUS: Record<string, StatusGroup> = {
  published: "published",
  manual_confirmed: "manual",
  reported_removed: "manual",
  failed: "failed",
  unknown: "unknown",
  running: "running",
  retry_pending: "running",
}

type StatusPost = { last_result?: { status?: string | null } | null }

export function postStatusGroup(post: StatusPost): StatusGroup {
  return GROUP_BY_STATUS[post.last_result?.status ?? ""] ?? "pending"
}

export function matchesStatusFilter(post: StatusPost, filter: PostStatusFilter): boolean {
  if (filter === "all") return true
  const group = postStatusGroup(post)
  return group === filter || (filter === "attention" && (group === "failed" || group === "unknown"))
}

export function countPostsByStatus(posts: StatusPost[]): Record<PostStatusFilter, number> {
  const counts = Object.fromEntries(STATUS_FILTERS.map(({ key }) => [key, 0])) as Record<PostStatusFilter, number>
  for (const post of posts) {
    for (const { key } of STATUS_FILTERS) if (matchesStatusFilter(post, key)) counts[key] += 1
  }
  return counts
}

/** Valor da URL (?status=) -> filtro; qualquer coisa desconhecida vira "all". */
export function parseStatusFilter(value: unknown): PostStatusFilter {
  return STATUS_FILTERS.some(({ key }) => key === value) ? (value as PostStatusFilter) : "all"
}

export const EMPTY_STATUS_MESSAGE: Record<PostStatusFilter, string> = {
  all: "Nenhum post encontrado com esse filtro.",
  attention: "Nenhum post com erro ou sem confirmação. Tudo em ordem.",
  unknown: "Nenhum post aguardando sua conferência.",
  failed: "Nenhum post com falha.",
  running: "Nenhuma publicação em execução agora.",
  pending: "Nenhum post agendado ou pendente.",
  published: "Nenhum post publicado ainda.",
  manual: "Nenhum post confirmado manualmente.",
}
