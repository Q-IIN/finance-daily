
// 版本号每次构建都会变，浏览器据此发现 SW 更新。
const BUILD = '8bfb34b5615c';
const CACHE = 'fd-' + BUILD;
const SHELL = ['./index.html', './manifest.webmanifest', './icons/icon-192.png'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(SHELL)).catch(() => {}).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// 策略：页面/JSON 一律网络优先（3.5s 超时），只有断网时才用缓存兜底；
// health.json 完全不缓存，保证“是否有新版本”的判断永远拿实时值。
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.endsWith('/health.json')) return;

  const isDoc = req.mode === 'navigate' || /\.(html|json)$/.test(url.pathname);
  if (isDoc) {
    e.respondWith((async () => {
      try {
        const res = await Promise.race([
          fetch(req, { cache: 'no-store' }),
          new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 3500))
        ]);
        if (res && res.ok) {
          const c = await caches.open(CACHE);
          c.put(req, res.clone()).catch(() => {});
          return res;
        }
        throw new Error('bad status');
      } catch (_) {
        const hit = await caches.match(req);
        if (hit) return hit;
        const idx = await caches.match('./index.html');
        return idx || Response.error();
      }
    })());
    return;
  }

  e.respondWith(
    caches.match(req).then(hit => {
      if (hit) return hit;
      return fetch(req).then(res => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
        }
        return res;
      });
    })
  );
});
