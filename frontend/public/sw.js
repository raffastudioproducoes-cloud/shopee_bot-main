// Service worker Auto Orbital. Torna o app instalável e abre o shell offline.
// Nunca toca em /api, nem em não-GET, nem em outra origem: dados de usuário só vão pela rede.
// Versão do cache vem de /sw.js?v=<VERSION do build> (ver main.tsx); build novo => cache novo.
const VERSION = new URL(self.location.href).searchParams.get('v') || '0'
const CACHE = `auto-orbital-${VERSION}`
const SHELL = '/'

self.addEventListener('install', () => self.skipWaiting())

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith('auto-orbital-') && k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return
  const url = new URL(request.url)
  if (url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return

  // Navegação: rede primeiro; offline cai no shell guardado.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((res) => {
          if (res.ok && res.headers.get('content-type')?.includes('text/html')) {
            const copy = res.clone()
            caches.open(CACHE).then((c) => c.put(SHELL, copy))
          }
          return res
        })
        .catch(() => caches.match(SHELL).then((r) => r || Response.error())),
    )
    return
  }

  // Só /assets/* (nomes com hash do Vite, imutáveis): cache primeiro.
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(
      caches.match(request).then(
        (hit) =>
          hit ||
          fetch(request).then((res) => {
            if (res.ok) {
              const copy = res.clone()
              caches.open(CACHE).then((c) => c.put(request, copy))
            }
            return res
          }),
      ),
    )
  }
})
