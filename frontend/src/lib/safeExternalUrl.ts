/**
 * Segunda barreira (S-02): o backend já recusa destinos externos na criação, mas dados
 * antigos ou adulterados não podem virar link clicável. Retorna undefined se não for seguro.
 */
const LINK_HOSTS = new Set(["shopee.com.br", "www.shopee.com.br", "s.shopee.com.br", "shope.ee"])
const IMAGE_HOSTS = new Set(["cf.shopee.com.br", "down-br.img.susercontent.com", "img.susercontent.com"])

function parseHttps(value: string | null | undefined): URL | null {
  if (!value || value.length > 2048 || value !== value.trim()) return null
  try {
    const url = new URL(value)
    if (url.protocol !== "https:" || url.username || url.password) return null
    if (url.port && url.port !== "443") return null
    return url
  } catch {
    return null
  }
}

export function safeExternalUrl(value: string | null | undefined): string | undefined {
  const url = parseHttps(value)
  if (!url || !LINK_HOSTS.has(url.hostname.toLowerCase()) || url.pathname === "/") return undefined
  return url.toString()
}

export function safeImageUrl(value: string | null | undefined): string | undefined {
  const url = parseHttps(value)
  if (!url) return undefined
  const host = url.hostname.toLowerCase()
  return IMAGE_HOSTS.has(host) || host.endsWith(".img.susercontent.com") ? url.toString() : undefined
}
