/* Service worker MemoAI Pro — généré au build par vite.config.ts (plugin « pwa-service-worker »).
 *
 * - Pré-cache l'application complète (HTML, JS, CSS, icônes) : elle s'ouvre même hors ligne.
 * - Navigation : réseau d'abord, puis l'application en cache si hors ligne.
 * - Fichiers /assets/* (noms versionnés) : cache d'abord.
 * - Polices Google : servies depuis le cache, rafraîchies en arrière-plan.
 * - Les appels à l'API Django ne sont JAMAIS mis en cache (données personnelles, jetons).
 */
const VERSION = '__BUILD_VERSION__';
const PRECACHE = `memoai-precache-${VERSION}`;
const RUNTIME = 'memoai-runtime-v1';
const PRECACHE_URLS = __PRECACHE_URLS__;
const STATIC_PATHS = [/^\/assets\//, /^\/icons\//, /^\/manifest\.webmanifest$/, /^\/favicon\.ico$/];
const FONT_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(PRECACHE).then(cache => cache.addAll(PRECACHE_URLS)));
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k.startsWith('memoai-precache-') && k !== PRECACHE).map(k => caches.delete(k)));
    if (self.registration.navigationPreload) await self.registration.navigationPreload.enable();
    await self.clients.claim();
  })());
});

// L'application demande l'activation immédiate quand l'utilisateur accepte la mise à jour.
self.addEventListener('message', event => {
  if (event.data === 'SKIP_WAITING') self.skipWaiting();
});

self.addEventListener('fetch', event => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);

  if (FONT_HOSTS.includes(url.hostname)) {
    event.respondWith(staleWhileRevalidate(request));
    return;
  }
  if (url.origin !== self.location.origin) return; // API Django et autres domaines : pas de cache

  if (request.mode === 'navigate') {
    event.respondWith(navigation(event));
    return;
  }
  if (STATIC_PATHS.some(re => re.test(url.pathname))) {
    event.respondWith(cacheFirst(request));
  }
  // Toute autre requête du même domaine (ex. API servie derrière le même nom) passe au réseau.
});

async function navigation(event) {
  try {
    const preloaded = await event.preloadResponse;
    if (preloaded) return preloaded;
    return await fetch(event.request);
  } catch {
    const cache = await caches.open(PRECACHE);
    return (await cache.match('/index.html')) || Response.error();
  }
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) (await caches.open(RUNTIME)).put(request, response.clone());
  return response;
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(RUNTIME);
  const cached = await cache.match(request);
  const network = fetch(request)
    .then(response => {
      if (response.ok || response.type === 'opaque') cache.put(request, response.clone());
      return response;
    })
    .catch(() => cached);
  return cached || network;
}
