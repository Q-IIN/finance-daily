
// 每次构建 BUILD 都变，浏览器据此发现 SW 更新。
const BUILD = '63a531d8667f';
const CACHE = 'fd-static-' + BUILD;
const ASSETS = ['./manifest.webmanifest', './icons/icon-192.png', './icons/icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS)).catch(() => {}).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.map(k => (k === CACHE ? null : caches.delete(k)))))
      .then(() => self.clients.claim())
  );
});

// 关键取舍：文档（HTML/JSON）一律直连网络，命中缓存就算输。
// 上一版是“网络 3.5 秒超时就回退缓存”，手机网络一慢就把昨天的页面端出来，
// 正是“明明更新了却看到旧内容”的元凶。现在断网时给一张离线页，绝不假装成功。
const OFFLINE = '<!doctype html><meta charset="utf-8">'
  + '<meta name="viewport" content="width=device-width,initial-scale=1">'
  + '<title>离线</title>'
  + '<body style="margin:0;font:16px/1.7 -apple-system,BlinkMacSystemFont,sans-serif;'
  + 'background:#0e1116;color:#e6e8eb;padding:64px 24px;text-align:center">'
  + '<p style="font-size:19px;font-weight:600;margin:0 0 10px">网络没通</p>'
  + '<p style="color:#8b93a1;font-size:14px;margin:0">拿不到最新一期，也不会给你看旧内容。<br>'
  + '检查网络后点下面重试。</p>'
  + '<p style="margin-top:32px"><a href="./index.html" style="display:inline-block;'
  + 'padding:13px 30px;border-radius:999px;background:#d4a54a;color:#0e1116;'
  + 'text-decoration:none;font-weight:600">重试</a></p>';

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  const isDoc = req.mode === 'navigate' || /\.(html|json|webmanifest)$/.test(url.pathname);
  if (isDoc) {
    e.respondWith(
      fetch(req, { cache: 'no-store' }).catch(
        () => new Response(OFFLINE, { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8' } })
      )
    );
    return;
  }

  // 静态资源（图标等）走缓存优先，它们不会变旧
  e.respondWith(
    caches.match(req).then(hit => hit || fetch(req).then(res => {
      if (res && res.ok) {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
      }
      return res;
    }).catch(() => Response.error()))
  );
});
