#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《财经》杂志页面生成器：把 magazine.json 渲染成期刊风格的阅读页。"""
import argparse
import json
import os

from build import CSS, esc, para_html  # noqa: E402

SECTION_ORDER = ["封面", "封面文章", "特别报道", "时事报道", "财经特稿", "资本与金融",
                 "环境与科技", "专栏", "其他"]

MAG_CSS = CSS + """
.mag-head{margin:20px 0 4px;padding:22px 20px;border-radius:var(--radius);
  background:linear-gradient(150deg,#1a2029,#12161d);
  border:1px solid var(--line);position:relative;overflow:hidden}
@media (prefers-color-scheme: light){.mag-head{background:linear-gradient(150deg,#fffdf7,#f7f1e3)}}
.mag-head::before{content:"";position:absolute;inset:0;
  background:radial-gradient(500px 200px at 90% -10%,rgba(212,165,74,.18),transparent 65%)}
.mag-kicker{font-size:10px;letter-spacing:3px;color:var(--gold);font-weight:700;text-transform:uppercase}
.mag-title{font-size:22px;font-weight:700;margin:6px 0 4px;letter-spacing:-.3px}
.mag-issue{font-size:13px;color:var(--fg2)}
.mag-issue b{color:var(--gold2)}
.mag-lead{font-size:12.5px;color:var(--fg3);margin-top:12px;line-height:1.7}
.sec-h{margin:24px 0 10px;font-size:13px;letter-spacing:1.6px;color:var(--gold);
  font-weight:700;text-transform:uppercase;display:flex;align-items:center;gap:8px}
.sec-h::after{content:"";flex:1;height:1px;background:var(--line)}
.lead-box{font-size:13.5px;color:var(--fg3);border-left:2px solid var(--gold);
  padding:2px 0 2px 12px;margin:0 0 12px;font-style:italic}
.exc{font-size:10px;color:var(--fg3);border:1px dashed var(--line);padding:1px 6px;border-radius:4px}
.full{font-size:10px;color:var(--down);border:1px solid var(--down);padding:1px 6px;border-radius:4px;opacity:.8}
"""


def sort_sections(articles):
    order = {k: i for i, k in enumerate(SECTION_ORDER)}
    return sorted(articles, key=lambda a: order.get(a.get("section") or "其他", 98))


def render_mag_card(a):
    badge = ('<span class="exc">节选 · 全文需订阅</span>' if a.get("excerpt_only")
             else '<span class="full">全文</span>')
    lead = f'<div class="lead-box">{esc(a["lead"])}</div>' if a.get("lead") else ""
    return f"""<article class="card" data-text="{esc((a['title']+' '+a['content'][:300]).lower())}">
  <div class="card-t">
    <span class="src" style="background:#8a1c1c">《财经》杂志</span>
    <span class="ch">{esc(a.get('section',''))}</span>{badge}
  </div>
  <h4><a href="{esc(a['url'])}" target="_blank" rel="noopener">{esc(a['title'])}</a></h4>
  {lead}
  <div class="body">{para_html(a['content'])}</div>
  <span class="more">展开全文</span>
</article>"""


def build_magazine_page(payload):
    arts = sort_sections(payload["articles"])
    groups, cur = {}, []
    for a in arts:
        groups.setdefault(a.get("section") or "其他", []).append(a)

    sections = []
    for sec, items in groups.items():
        sections.append(f'<div class="sec-h">{esc(sec)}</div>' +
                        "".join(render_mag_card(a) for a in items))

    full_n = sum(1 for a in arts if not a.get("excerpt_only"))
    total_chars = sum(a["chars"] for a in arts)
    issue = payload.get("issue") or "最新一期"
    pub = payload.get("publish_date") or ""

    nav = """<nav class="nav">
  <a href="index.html"><b>▤</b>今日</a><a href="index.html#cat-macro"><b>◈</b>分类</a>
  <a href="#q" onclick="document.getElementById('q').focus()"><b>⌕</b>搜索</a>
  <a href="magazine.html" class="on"><b>▦</b>杂志</a>
  <a href="archive.html"><b>☰</b>往期</a></nav>"""

    return f"""<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>《财经》杂志 · {esc(issue)}</title>
<meta name="theme-color" content="#0e1116">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icons/icon-192.png">
<style>{MAG_CSS}</style></head><body>
<div class="wrap">
<div class="mag-head">
  <div class="mag-kicker">Caijing Magazine · Weekly</div>
  <div class="mag-title">《财经》杂志</div>
  <div class="mag-issue"><b>{esc(issue)}</b>{' · 出版 ' + esc(pub) if pub else ''}</div>
  <div class="mag-lead">每周三自动更新当期网上公开文章 · 本期 {len(arts)} 篇（全文 {full_n} 篇 / 节选 {len(arts)-full_n} 篇）· 约 {total_chars//1000}k 字 · 采集于 {esc(payload.get('fetched_at','')[:16])}</div>
</div>

<div class="toolbar" style="margin-top:12px">
  <input id="q" class="search" type="search" placeholder="搜索本期文章…" autocomplete="off">
</div>

{''.join(sections)}

<footer>《财经》杂志网上免费公开版含部分全文与部分节选；节选文章完整版需订阅杂志。<br>内容版权归《财经》杂志所有，仅供个人阅读。</footer>
</div>
{nav}
<script>
(function(){{
  var q=document.getElementById('q');
  var cards=[].slice.call(document.querySelectorAll('.card'));
  if(q) q.addEventListener('input',function(){{
    var t=q.value.trim().toLowerCase();
    cards.forEach(function(c){{c.style.display=!t||c.dataset.text.indexOf(t)>-1?'':'none'}});
  }});
  document.addEventListener('click',function(e){{
    var m=e.target.closest('.more'); if(!m) return;
    var card=m.closest('.card'); card.classList.toggle('open');
    m.textContent=card.classList.contains('open')?'收起全文':'展开全文';
  }});
}})();
</script>
</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="/workspace/finance-daily/data/magazine.json")
    ap.add_argument("--out", default="/workspace/finance-daily")
    args = ap.parse_args()
    with open(args.data, encoding="utf-8") as f:
        payload = json.load(f)
    html = build_magazine_page(payload)
    path = os.path.join(args.out, "magazine.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✓ 杂志页已生成 → {path}（{payload['total']} 篇）")


if __name__ == "__main__":
    main()
