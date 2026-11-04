/** Only the explicit creation intent is accepted; arbitrary search input is ignored. */
export function creationSearch(search: Record<string, unknown>): { action?: 'create' } {
  return search.action === 'create' ? { action: 'create' } : {}
}
