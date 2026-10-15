/** Admin que saiu do /admin para ver o site de cliente: enquanto a flag existir,
 * o redirecionamento automático de ADMIN para /admin não dispara. */
const KEY = 'orbital:admin-visiting-site'

export const isAdminVisitingSite = (): boolean => {
  try { return sessionStorage.getItem(KEY) === '1' } catch { return false }
}
export const setAdminVisitingSite = (): void => {
  try { sessionStorage.setItem(KEY, '1') } catch { /* sessionStorage indisponível */ }
}
export const clearAdminVisitingSite = (): void => {
  try { sessionStorage.removeItem(KEY) } catch { /* sessionStorage indisponível */ }
}
