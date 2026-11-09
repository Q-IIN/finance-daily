#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日报生成器：把采集到的 JSON 渲染成移动端优先的 HTML 日报 + Markdown + PWA 外壳。"""
import argparse
import json
import os
import re
import shutil
from datetime import datetime

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CATEGORY_ICON = {
    "macro": "◈", "market": "◎", "company": "▣",
    "finance": "◇", "regulation": "⚖", "global": "⊕",
    "tech": "◆", "other": "▪",
}

SOURCE_COLOR = {
    "stcn": "#c0392b", "cs": "#1f6fb2", "yicai": "#0f8a7d",
    "reuters": "#e07b00", "ft": "#a0284a", "economist": "#b8232f",
}

# ------------------------------------------------------------------ 样式

CSS = """
:root{
  --bg:#0e1116; --bg2:#151a22; --card:#1a2029; --line:#262e3a;
  --fg:#e8ecf1; --fg2:#a4b0c0; --fg3:#6c7a8c;
  --gold:#d4a54a; --gold2:#f0c674; --accent:#4a9eff;
  --up:#e04a4a; --down:#2fa96b;
  --radius:14px;
}
@media (prefers-color-scheme: light){
  :root{ --bg:#f5f6f8; --bg2:#ffffff; --card:#ffffff; --line:#e4e8ee;
    --fg:#141a22; --fg2:#4d5a6b; --fg3:#8a96a6; --gold:#9a7420; --gold2:#b8892c;
    --accent:#1a66c9; }
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;padding:0}
body{
  background:var(--bg); color:var(--fg);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  font-size:16px; line-height:1.7; -webkit-font-smoothing:antialiased;
  padding-bottom:calc(56px + env(safe-area-inset-bottom));
}
.wrap{max-width:760px;margin:0 auto;padding:0 16px}

/* header */
header{
  position:relative;padding:calc(26px + env(safe-area-inset-top)) 0 18px;
  border-bottom:1px solid var(--line);
  background:linear-gradient(180deg,rgba(212,165,74,.10),transparent 85%);
}
.brand{display:flex;align-items:baseline;gap:9px}
.brand h1{
  font-size:25px;margin:0;letter-spacing:-.4px;font-weight:700;
  background:linear-gradient(96deg,var(--gold2),var(--gold));
  -webkit-background-clip:text;background-clip:text;color:transparent;
}
.brand .en{font-size:10px;letter-spacing:2.2px;color:var(--fg3);text-transform:uppercase}
.meta{margin-top:9px;font-size:12.5px;color:var(--fg3);
  display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center}
.meta b{color:var(--fg2);font-weight:600}
.live{display:inline-flex;align-items:center;gap:5px;color:var(--down);font-weight:600}
.live i{width:6px;height:6px;border-radius:50%;background:var(--down);
  box-shadow:0 0 0 0 rgba(47,169,107,.6);animation:pulse 2.2s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(47,169,107,.5)}70%{box-shadow:0 0 0 7px rgba(47,169,107,0)}100%{box-shadow:0 0 0 0 rgba(47,169,107,0)}}

/* 今日速览 */
.brief{
  margin:18px 0 4px;padding:16px 18px;border-radius:var(--radius);
  background:var(--bg2);border:1px solid var(--line);
  border-left:3px solid var(--gold);
}
.brief h2{font-size:12px;letter-spacing:1.4px;color:var(--gold);margin:0 0 10px;
  font-weight:700;text-transform:uppercase}
.brief ul{margin:0;padding-left:16px}
.brief li{font-size:14px;color:var(--fg2);margin-bottom:6px;line-height:1.55}
.brief li a{color:var(--fg2)}

/* 搜索 + 筛选 */
.toolbar{position:sticky;top:0;z-index:30;background:var(--bg);
  padding:11px 0 9px;border-bottom:1px solid var(--line);margin-top:16px}
body{scroll-padding-top:60px}
.search{width:100%;padding:10px 13px;border-radius:11px;border:1px solid var(--line);
  background:var(--bg2);color:var(--fg);font-size:14px;outline:none;font-family:inherit}
.search:focus{border-color:var(--gold)}
.search::placeholder{color:var(--fg3)}
.chips{display:flex;gap:7px;overflow-x:auto;margin-top:9px;padding-bottom:2px;
  scrollbar-width:none}
.chips::-webkit-scrollbar{display:none}
.chip{flex:0 0 auto;padding:5px 12px;border-radius:99px;border:1px solid var(--line);
  background:var(--bg2);color:var(--fg2);font-size:12.5px;cursor:pointer;
  white-space:nowrap;transition:.16s;font-family:inherit}
.chip.on{background:var(--gold);border-color:var(--gold);color:#1a1206;font-weight:600}

/* 分类区 */
.cat{margin-top:26px;scroll-margin-top:96px}
.cat-h{display:flex;align-items:center;gap:9px;margin-bottom:11px;
  padding-bottom:8px;border-bottom:1px solid var(--line)}
.cat-h .ic{color:var(--gold);font-size:15px}
.cat-h h3{font-size:15px;margin:0;font-weight:700;letter-spacing:.3px}
.cat-h .n{font-size:11px;color:var(--fg3);background:var(--bg2);
  border:1px solid var(--line);padding:1px 7px;border-radius:99px}

/* 卡片 */
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  padding:15px 16px;margin-bottom:11px;transition:.18s}
.card:active{transform:scale(.995)}
.card-t{display:flex;gap:7px;align-items:center;margin-bottom:8px;flex-wrap:wrap}
.src{font-size:10.5px;font-weight:700;padding:2px 7px;border-radius:4px;
  color:#fff;letter-spacing:.2px}
.ch{font-size:11px;color:var(--fg3);border:1px solid var(--line);padding:1px 6px;border-radius:4px}
.tm{font-size:11px;color:var(--fg3);margin-left:auto;font-variant-numeric:tabular-nums}
.card h4{margin:0 0 9px;font-size:16.5px;line-height:1.42;font-weight:600;letter-spacing:-.2px}
.card h4 a{color:var(--fg);text-decoration:none}
.body{font-size:14.5px;line-height:1.78;color:var(--fg2);
  max-height:5.5em;overflow:hidden;position:relative;transition:max-height .3s}
.body::after{content:"";position:absolute;left:0;right:0;bottom:0;height:2.4em;
  background:linear-gradient(transparent,var(--card))}
.card.open .body{max-height:none}
.card.open .body::after{display:none}
.body p{margin:0 0 .7em}
.more{margin-top:8px;font-size:12.5px;color:var(--gold);cursor:pointer;
  display:inline-block;font-weight:600;user-select:none}
.pw{display:inline-block;font-size:10.5px;color:var(--fg3);border:1px dashed var(--line);
  padding:1px 6px;border-radius:4px;margin-left:6px}
.sum-only{font-size:14px;color:var(--fg2);font-style:normal}

/* footer */
footer{margin:36px 0 10px;padding-top:18px;border-top:1px solid var(--line);
  font-size:11.5px;color:var(--fg3);line-height:1.85}
footer a{color:var(--fg2)}

/* 底部导航 */
.nav{position:fixed;left:0;right:0;bottom:0;z-index:40;display:flex;
  background:rgba(14,17,22,.92);backdrop-filter:blur(14px);
  border-top:1px solid var(--line);padding-bottom:env(safe-area-inset-bottom)}
@media (prefers-color-scheme: light){.nav{background:rgba(255,255,255,.93)}}
.nav a{flex:1;text-align:center;padding:9px 0 7px;font-size:10.5px;
  color:var(--fg3);text-decoration:none;line-height:1.3}
.nav a b{display:block;font-size:16px;font-weight:400;margin-bottom:1px}
.nav a.on{color:var(--gold)}

.empty{text-align:center;padding:60px 20px;color:var(--fg3);font-size:14px}
@media (min-width:700px){
  body{font-size:16.5px}
  .card{padding:18px 20px}
  .card h4{font-size:18px}
}
"""

JS = """
(function(){
  var q=document.getElementById('q'), chips=[].slice.call(document.querySelectorAll('.chip'));
  var cards=[].slice.call(document.querySelectorAll('.card')), cats=[].slice.call(document.querySelectorAll('.cat'));
  var state={text:'', cat:'all'};

  function apply(){
    cards.forEach(function(c){
      var t=c.dataset.text, cat=c.dataset.cat;
      var okT=!state.text||t.indexOf(state.text)>-1;
      var okC=state.cat==='all'||cat===state.cat;
      c.style.display=(okT&&okC)?'':'none';
    });
    cats.forEach(function(s){
      var vis=s.querySelectorAll('.card:not([style*="display: none"])').length;
      s.style.display=vis?'':'none';
    });
  }
  if(q) q.addEventListener('input',function(){ state.text=q.value.trim().toLowerCase(); apply(); });
  chips.forEach(function(ch){
    ch.addEventListener('click',function(){
      chips.forEach(function(x){x.classList.remove('on')});
      ch.classList.add('on'); state.cat=ch.dataset.cat; apply();
      if(state.cat!=='all'){
        var el=document.getElementById('cat-'+state.cat);
        if(el) window.scrollTo({top:el.offsetTop-92,behavior:'smooth'});
      }
    });
  });
  document.addEventListener('click',function(e){
    var m=e.target.closest('.more'); if(!m) return;
    var card=m.closest('.card'); card.classList.toggle('open');
    m.textContent=card.classList.contains('open')?'收起全文':'展开全文';
  });
})();
"""


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def para_html(text):
    parts = [p.strip() for p in re.split(r"\n+", text or "") if p.strip()]
    if not parts:
        return ""
    return "".join(f"<p>{esc(p)}</p>" for p in parts)


def time_short(published):
    if not published:
        return ""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})[ T](\d{2}:\d{2})", published)
    if m:
        return f"{m.group(2)}/{m.group(3)} {m.group(4)}"
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", published)
    return m.group(0)[5:] if m else published[:16]




def magazine_banner(data_dir, base=""):
    path = os.path.join(data_dir, "magazine.json")
    if not os.path.exists(path):
        return ""
    try:
        with open(path, encoding="utf-8") as f:
            m = json.load(f)
    except Exception:
        return ""
    if not m.get("articles"):
        return ""
    first = m["articles"][0]["title"]
    return f'''<a href="{base}magazine.html" style="display:flex;gap:12px;align-items:center;margin-top:12px;padding:13px 16px;border-radius:var(--radius);background:linear-gradient(120deg,rgba(138,28,28,.22),rgba(212,165,74,.10));border:1px solid var(--line);text-decoration:none">
  <span style="font-size:20px">▦</span>
  <span style="flex:1;font-size:13px;color:var(--fg2);line-height:1.5">《财经》杂志 <b style="color:var(--gold2)">{esc(m.get("issue",""))}</b> 已更新 · {m["total"]} 篇<br><span style="color:var(--fg3);font-size:12px">本期主打：{esc(first[:32])}</span></span>
  <span style="color:var(--gold);font-size:12px">进入 →</span>
</a>'''

def render_card(a):
    color = SOURCE_COLOR.get(a["source_id"], "#666")
    is_full = a.get("fulltext")
    long_enough = (a.get("chars") or 0) > 300
    body_cls = "body" if is_full else "body sum-only"
    badge = '<span class="pw">付费墙</span>' if a.get("paywalled") else ""
    link = f'<a href="{esc(a["url"])}" target="_blank" rel="noopener">{esc(a["title"])}</a>' if a.get("url") else esc(a["title"])
    more = '<span class="more">展开全文</span>' if (is_full and long_enough) else ""
    if not is_full:
        more = f'<a class="more" href="{esc(a["url"])}" target="_blank" rel="noopener">阅读原文 →</a>' if a.get("url") else ""
    return f"""<article class="card" data-cat="{a['category']}" data-text="{esc((a['title']+' '+a['content'][:300]).lower())}">
  <div class="card-t">
    <span class="src" style="background:{color}">{esc(a['source'])}</span>
    <span class="ch">{esc(a.get('channel',''))}</span>{badge}
    <span class="tm">{time_short(a.get('published',''))}</span>
  </div>
  <h4>{link}</h4>
  <div class="{body_cls}">{para_html(a.get('content',''))}</div>
  {more}
</article>"""


def build_page(payload, all_dates, active="today", base="", banner=""):
    arts = payload["articles"]
    cats = []
    for a in arts:
        if a["category"] not in [c[0] for c in cats]:
            cats.append((a["category"], a["category_label"]))

    # 今日速览：每分类头 1 条，最多 6 条
    brief_items, used = [], set()
    for key, label in cats:
        for a in arts:
            if a["category"] == key and key not in used and (a.get("chars") or 0) > 60:
                used.add(key)
                brief_items.append((label, a))
                break
    brief_html = "".join(
        f'<li><b style="color:var(--fg)">{esc(l)}</b> · {esc(a["title"])}</li>'
        for l, a in brief_items[:7]
    )

    chips = '<button class="chip on" data-cat="all">全部</button>' + "".join(
        f'<button class="chip" data-cat="{k}">{esc(v)}</button>' for k, v in cats
    )

    sections = []
    for key, label in cats:
        group = [a for a in arts if a["category"] == key]
        sections.append(f"""<section class="cat" id="cat-{key}">
  <div class="cat-h"><span class="ic">{CATEGORY_ICON.get(key,'▪')}</span>
    <h3>{esc(label)}</h3><span class="n">{len(group)}</span></div>
  {''.join(render_card(a) for a in group)}
</section>""")

    stats = payload.get("per_source_names") or payload.get("per_source", {})
    src_stat = " · ".join(f"{k} {v}" for k, v in stats.items())
    total_chars = sum(a.get("chars", 0) for a in arts)
    date_cn = payload["date"]
    gen = payload.get("generated_at", "")[:16]

    nav = f"""<nav class="nav">
  <a href="{base}index.html" class="{'on' if active=='today' else ''}"><b>▤</b>今日</a>
  <a href="#cat-macro"><b>◈</b>分类</a>
  <a href="#q" onclick="document.getElementById('q').focus()"><b>⌕</b>搜索</a>
  <a href="{base}magazine.html"><b>▦</b>杂志</a>
  <a href="{base}archive.html"><b>☰</b>往期</a>
</nav>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,maximum-scale=5">
<title>财经日报 {date_cn}</title>
<meta name="theme-color" content="#0e1116">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="manifest" href="{base}manifest.webmanifest">
<link rel="apple-touch-icon" href="{base}icons/icon-192.png">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="brand"><h1>财经日报</h1><span class="en">Daily Briefing</span></div>
  <div class="meta">
    <span><b>{date_cn}</b></span>
    <span class="live"><i></i>已更新 {gen[11:]}</span>
    <span><b>{len(arts)}</b> 篇</span>
    <span><b>{total_chars//1000}k</b> 字</span>
  </div>
</header>

<div class="brief">
  <h2>Today's Focus · 今日速览</h2>
  <ul>{brief_html}</ul>
</div>
{banner}
<div class="toolbar">
  <input id="q" class="search" type="search" placeholder="搜索标题或正文关键词…" autocomplete="off">
  <div class="chips">{chips}</div>
</div>

{''.join(sections)}

<footer>
  数据来源：{esc(src_stat)}<br>
  国内三家（证券时报 / 中国证券报 / 第一财经）为正文全文；Reuters、FT、经济学人经 RSS 代理获取标题与摘要，原文需订阅或访问原站。<br>
  生成于 {esc(payload.get('generated_at',''))} · 内容版权归原媒体所有。
</footer>
</div>
{nav}
<script>{JS}</script>
</body>
</html>"""


def build_archive(payloads, out_dir):
    rows = []
    for p in sorted(payloads, key=lambda x: x["date"], reverse=True):
        rows.append(f"""<a class="card" href="daily/{p['date']}.html" style="display:block;text-decoration:none">
  <div class="card-t"><span class="src" style="background:var(--gold)">{p['date']}</span>
    <span class="tm">{p['total']} 篇</span></div>
  <h4 style="margin:0">{esc(p['articles'][0]['title'] if p['articles'] else '（无内容）')}</h4>
</a>""")
    nav = """<nav class="nav">
  <a href="index.html"><b>▤</b>今日</a><a href="#"><b>◈</b>分类</a>
  <a href="index.html#q"><b>⌕</b>搜索</a><a href="magazine.html"><b>▦</b>杂志</a><a href="archive.html" class="on"><b>☰</b>往期</a></nav>"""
    return f"""<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>往期归档</title><meta name="theme-color" content="#0e1116">
<link rel="manifest" href="manifest.webmanifest"><style>{CSS}</style></head><body>
<div class="wrap"><header><div class="brand"><h1>往期归档</h1><span class="en">Archive</span></div>
<div class="meta"><span>共 <b>{len(payloads)}</b> 期</span></div></header>
<div style="margin-top:20px">{''.join(rows)}</div>
<footer>点击任意一期查看当日完整日报。</footer></div>{nav}</body></html>"""


MANIFEST = {
    "name": "财经日报 Daily Briefing",
    "short_name": "财经日报",
    "description": "证券时报 · 中国证券报 · 第一财经 · Reuters · FT · 经济学人 每日资讯汇总",
    "start_url": "./index.html",
    "scope": "./",
    "display": "standalone",
    "orientation": "portrait",
    "background_color": "#0e1116",
    "theme_color": "#0e1116",
    "lang": "zh-CN",
    "icons": [
        {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
}

SW = """
const CACHE = 'fd-v1';
const SHELL = ['./index.html', './manifest.webmanifest', './icons/icon-192.png'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request).then(res => {
      const copy = res.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy)).catch(() => {});
      return res;
    }).catch(() => caches.match(e.request).then(r => r || caches.match('./index.html')))
  );
});
"""


def snake(a):
    return f"{a['source']} · {a['channel']}"


def build_markdown(payload):
    lines = [f"# 财经日报 · {payload['date']}", "",
             f"> 生成时间 {payload['generated_at']} · 共 {payload['total']} 篇", ""]
    cats = []
    for a in payload["articles"]:
        if a["category_label"] not in cats:
            cats.append(a["category_label"])
    for label in cats:
        lines.append(f"## {label}")
        lines.append("")
        for a in payload["articles"]:
            if a["category_label"] != label:
                continue
            tag = "" if a.get("fulltext") else " `摘要`"
            lines.append(f"### {a['title']}{tag}")
            lines.append(f"*{snake(a)} · {a.get('published','')}*")
            lines.append("")
            body = a.get("content", "").strip()
            lines.append(body if a.get("fulltext") else body)
            lines.append("")
            if a.get("url"):
                lines.append(f"[原文]({a['url']})")
                lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="/workspace/finance-daily/data")
    ap.add_argument("--out", default="/workspace/finance-daily")
    args = ap.parse_args()

    os.makedirs(os.path.join(args.out, "daily"), exist_ok=True)
    os.makedirs(os.path.join(args.out, "icons"), exist_ok=True)
    os.makedirs(os.path.join(args.out, "md"), exist_ok=True)

    payloads = []
    for fn in sorted(os.listdir(args.data)):
        if re.match(r"^\d{4}-\d{2}-\d{2}\.json$", fn):
            with open(os.path.join(args.data, fn), encoding="utf-8") as f:
                payloads.append(json.load(f))
    if not payloads:
        raise SystemExit("没有找到任何采集数据，请先运行 fetch.py")

    latest = max(payloads, key=lambda p: p["date"])

    # 每日独立页
    for p in payloads:
        html = build_page(p, [x["date"] for x in payloads], base="../", banner=magazine_banner(args.data, "../"))
        with open(os.path.join(args.out, "daily", f"{p['date']}.html"), "w", encoding="utf-8") as f:
            f.write(html)
        with open(os.path.join(args.out, "md", f"{p['date']}.md"), "w", encoding="utf-8") as f:
            f.write(build_markdown(p))

    # 首页 = 最新一期（相对路径修正：daily 页里的资源路径是 ../）
    index_html = build_page(latest, [x["date"] for x in payloads], banner=magazine_banner(args.data))
    with open(os.path.join(args.out, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    with open(os.path.join(args.out, "archive.html"), "w", encoding="utf-8") as f:
        f.write(build_archive(payloads, args.out))

    with open(os.path.join(args.out, "manifest.webmanifest"), "w", encoding="utf-8") as f:
        json.dump(MANIFEST, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.out, "sw.js"), "w", encoding="utf-8") as f:
        f.write(SW)

    print(f"✓ 生成 {len(payloads)} 期日报 → {args.out}")
    print(f"✓ 最新：{latest['date']}，{latest['total']} 篇")


if __name__ == "__main__":
    main()
