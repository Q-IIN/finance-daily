#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《财经》杂志采集器：抓当期期号、目录与全部可公开文章。

《财经》为周刊（每周一出版），网上免费公开每期数篇精选的节选
（封面文章、特别报道、栏目文章），完整版需订阅。

用法:
    python3 fetch_magazine.py --out /workspace/finance-daily/data
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch import http_get, clean_text, strip_noise  # noqa: E402

HOME = "https://magazine.caijing.com.cn/"
ART_RE = re.compile(r"(?:https?:)?//magazine\.caijing\.com\.cn/(\d{8})/(\d+)\.shtml")
ISSUE_URL_RE = re.compile(r"//magazine\.caijing\.com\.cn/caijingmagazine/(\d{4}/\d+)/")


def parse_issue_meta(home_html):
    """从首页提取期号与出版日期。"""
    m = re.search(r"(20\d{2}年第\d+期[^<]*总第\d+期)", home_html)
    issue = clean_text(m.group(1)) if m else ""
    m2 = re.search(r"出版日期[：:]\s*(20\d{2}-\d{2}-\d{2})", home_html)
    pub = m2.group(1) if m2 else ""
    return issue, pub


def collect_article_links(url, html):
    links = {}
    for m in ART_RE.finditer(html):
        date, aid = m.groups()
        links[aid] = f"https://magazine.caijing.com.cn/{date}/{aid}.shtml"
    return links


def extract_article(html):
    soup = BeautifulSoup(html, "html.parser")
    title = ""
    if soup.title:
        title = soup.title.get_text().split("_")[0].strip()
    node = soup.select_one("div.article-content") or soup.select_one("div.magazine_art")
    if not node:
        return title, "", "", ""
    paras = [p.get_text(" ", strip=True) for p in node.find_all(["p"])]
    body = "\n".join(p for p in paras if len(p) > 8)
    body = strip_noise(clean_text(body))

    excerpt = "获取全部精彩内容" in body or "......" in body
    # 栏目：标题形如 名称_栏目_...
    section = ""
    if soup.title:
        parts = soup.title.get_text().split("_")
        if len(parts) >= 3:
            section = parts[1].strip()
    # 导语
    lead = ""
    lead_node = soup.find(string=re.compile(r"^导语$"))
    if lead_node:
        nxt = lead_node.find_parent().find_next_sibling()
        if nxt:
            lead = clean_text(nxt.get_text(" ", strip=True))
    return title, body, section, lead


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/workspace/finance-daily/data")
    args = ap.parse_args()

    print("① 读取杂志首页…")
    home = http_get(HOME, timeout=18)
    issue, pub = parse_issue_meta(home)
    print(f"  当期：{issue or '未识别'}  出版日期：{pub or '未识别'}")

    links = collect_article_links(HOME, home)
    print(f"  首页文章：{len(links)} 篇")

    m = ISSUE_URL_RE.search(home)
    if m:
        issue_url = f"https://magazine.caijing.com.cn/caijingmagazine/{m.group(1)}/"
        try:
            page = http_get(issue_url, timeout=18)
            more = collect_article_links(issue_url, page)
            for k, v in more.items():
                links.setdefault(k, v)
            print(f"  目录页合并后：{len(links)} 篇")
        except Exception as exc:  # noqa: BLE001
            print(f"  [warn] 目录页失败：{exc}", file=sys.stderr)

    articles = []
    for url in sorted(links.values()):
        try:
            html = http_get(url, timeout=18)
            title, body, section, lead = extract_article(html)
        except Exception as exc:  # noqa: BLE001
            print(f"  [warn] 正文失败 {url}: {exc}", file=sys.stderr)
            continue
        if not title or len(body) < 150:
            continue
        excerpt_only = "获取全部精彩内容" in body or "智选好店订阅" in body
        articles.append({
            "source": "《财经》杂志",
            "source_id": "caijing_mag",
            "title": title,
            "url": url,
            "section": section,
            "lead": lead,
            "content": body,
            "chars": len(body),
            "excerpt_only": excerpt_only,
        })
        tag = "节选" if excerpt_only else "全文"
        print(f"  ✓ {title[:26]} | {section or '—'} | {len(body)} 字 [{tag}]")
        time.sleep(0.5)

    payload = {
        "magazine": "《财经》杂志",
        "issue": issue,
        "publish_date": pub,
        "fetched_at": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
        "total": len(articles),
        "articles": articles,
    }
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "magazine.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"\n共 {len(articles)} 篇 → {path}")


if __name__ == "__main__":
    main()
