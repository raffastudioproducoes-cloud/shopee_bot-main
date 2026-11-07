/** Quantidade visível por página no histórico de publicações. */
export const POSTS_PER_PAGE = 15

/** Lote múltiplo de 15: navegação em cache sem páginas incompletas artificiais. */
export const POSTS_FETCH_LIMIT = 90

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
