// Service worker do Auto Orbital (legado) — só cuida de cache de asset estático
// pra funcionar como PWA (instalar, abrir offline o shell).
// NUNCA intercepta POST/PUT/DELETE nem rotas dinâmicas (/posts, /products,
// /panel/*, etc.) pra não arriscar cache de resposta de agendamento/
// publicação do bot. Só GET de /static/ passa pelo cache.

const CACHE_NAME = "auto-orbital-static-v1";
const STATIC_PATH_PREFIX = "/static/";

self.addEventListener("install", (event) => {
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((key) => key !== CACHE_NAME)
                    .map((key) => caches.delete(key))
            )
        )
    );
    self.clients.claim();
});

self.addEventListener("fetch", (event) => {
    const { request } = event;

    // só cache de GET de assets estáticos — todo o resto (páginas,
    // formulários, APIs, agendamento) vai direto pra rede, sempre.
    if (request.method !== "GET") {
        return;
    }

    const url = new URL(request.url);
    if (url.origin !== self.location.origin) {
        return;
    }
    if (!url.pathname.startsWith(STATIC_PATH_PREFIX)) {
        return;
    }

    event.respondWith(
        caches.open(CACHE_NAME).then((cache) =>
            cache.match(request).then((cached) => {
                const networkFetch = fetch(request)
                    .then((response) => {
                        if (response.ok) {
                            cache.put(request, response.clone());
                        }
                        return response;
                    })
                    .catch(() => cached);

                return cached || networkFetch;
            })
        )
    );
});
