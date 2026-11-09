/** Quantidade visível por página no histórico de publicações. */
export const POSTS_PER_PAGE = 15

/** Lote múltiplo de 15: navegação em cache sem páginas incompletas artificiais. */
export const POSTS_FETCH_LIMIT = 30

/** Pagina somente resultados do perfil ativo já recebidos da API. */
export function paginatePostHistory<T>(items: readonly T[], requestedPage: number) {
  const loadedPages = Math.max(1, Math.ceil(items.length / POSTS_PER_PAGE))
  const safePage = Number.isFinite(requestedPage) ? Math.trunc(requestedPage) : 1
  const page = Math.max(1, Math.min(safePage, loadedPages))
  const start = (page - 1) * POSTS_PER_PAGE
  return { page, loadedPages, items: items.slice(start, start + POSTS_PER_PAGE) }
}

/** Na busca, só libera a próxima página quando houver resultados filtrados. */
export function canAdvancePostHistory(
  page: number,
  loadedPages: number,
  hasMoreRemotePages: boolean,
  searchActive: boolean,
): boolean {
  return page < loadedPages || (!searchActive && hasMoreRemotePages)
}

type PollablePost = {
  scheduled?: boolean
  last_result?: { status?: string | null } | null
}

/**
 * Quanto esperar para atualizar a lista de Posts sozinha.
 * Antes: com qualquer post agendado a tela recarregava TODAS as páginas carregadas a cada 30 s,
 * para sempre (uma conta com centenas de posts agendados nunca parava de consultar).
 * Agora: 30 s só enquanto há envio em andamento ou nova tentativa na fila; 5 min se só há agendados.
 */
export function postsRefreshInterval(posts: PollablePost[]): number | false {
  if (posts.some((post) => post.last_result?.status === "running" || post.last_result?.status === "retry_pending")) {
    return 30_000
  }
  return posts.some((post) => post.scheduled) ? 5 * 60_000 : false
}
