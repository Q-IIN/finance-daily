#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""金融资讯采集器：多源抓取 + 全文提取 + 去重 + 分类。

用法:
    python3 fetch.py --out /workspace/finance-daily/data
    python3 fetch.py --only stcn,yicai --limit 5
"""
import argparse
import gzip
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from bs4 import BeautifulSoup

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(SKILL_DIR, "config", "sources.json")

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]

NOISE_PATTERNS = [
    r"责任编辑[:：].*", r"免责声明.*", r"本文首发于.*", r"扫描二维码.*",
    r"更多精彩内容.*", r"点击(进入|查看).*", r"版权(声明|所有).*",
    r"（?完）?$", r"^原标题[:：]", r"证券时报.*记者.*",
]


# ---------------------------------------------------------------- HTTP

def http_get(url, timeout=18, retries=2, headers=None):
    """带重试与 gzip 处理的 GET，返回 str。"""
    last_err = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers=headers or {})
        req.add_header("User-Agent", UA_POOL[attempt % len(UA_POOL)])
        req.add_header("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
        req.add_header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                charset = "utf-8"
                ctype = resp.headers.get("Content-Type", "")
                m = re.search(r"charset=([\w-]+)", ctype, re.I)
                if m:
                    charset = m.group(1)
                else:
                    m2 = re.search(rb'charset=["\']?([\w-]+)', raw[:2000], re.I)
                    if m2:
                        charset = m2.group(1).decode("ascii", "ignore")
                try:
                    return raw.decode(charset, "ignore")
                except LookupError:
                    return raw.decode("utf-8", "ignore")
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(0.8 * (attempt + 1))
    raise last_err


# ---------------------------------------------------------------- 正文提取

def clean_text(text):
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    text = re.sub(r"[ \t\u3000]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_by_selectors(soup, selectors):
    for sel in selectors:
        try:
            node = soup.select_one(sel)
        except Exception:  # noqa: BLE001
            continue
        if not node:
            continue
        paras = [p.get_text(" ", strip=True) for p in node.find_all("p")]
        body = "\n".join(p for p in paras if len(p) > 12)
        if len(body) < 120:
            body = node.get_text("\n", strip=True)
        body = clean_text(body)
        if len(body) >= 120:
            return body
    return ""


def extract_by_density(soup):
    """通用兜底：选出 <p> 文本总量最大的容器。"""
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        tag.decompose()
    best, best_score = None, 0
    for node in soup.find_all(["div", "article", "section", "td"]):
        ps = node.find_all("p", recursive=True)
        if len(ps) < 2:
            continue
        total = sum(len(p.get_text(strip=True)) for p in ps)
        # 惩罚链接密度高的容器（导航/列表）
        link_len = sum(len(a.get_text(strip=True)) for a in node.find_all("a"))
        score = total - link_len * 1.6
        if score > best_score:
            best, best_score = node, score
    if best is None:
        return ""
    paras = [p.get_text(" ", strip=True) for p in best.find_all("p")]
    body = "\n".join(p for p in paras if len(p) > 12)
    return clean_text(body)


def strip_noise(text):
    lines = []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if len(s) < 8:
            continue
        if any(re.search(p, s) for p in NOISE_PATTERNS):
            continue
        lines.append(s)
    return "\n".join(lines).strip()


def extract_article(html, selectors):
    soup = BeautifulSoup(html, "html.parser")
    title = ""
    for prop in ["og:title", "twitter:title"]:
        meta = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
        if meta and meta.get("content"):
            title = meta["content"].strip()
            break
    if not title and soup.title:
        title = soup.title.get_text(strip=True)
        title = re.split(r"[_|｜\-—]\s*(证券时报|中证网|第一财经|财联社)", title)[0].strip()

    body = extract_by_selectors(soup, selectors or []) or extract_by_density(soup)
    body = strip_noise(body)

    published = ""
    for prop in ["article:published_time", "pubdate", "publishdate", "og:release_date"]:
        meta = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
        if meta and meta.get("content"):
            published = meta["content"].strip()
            break
    if not published:
        m = re.search(r"(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})日?\s*(\d{1,2}):(\d{2})", html)
        if m:
            y, mo, d, hh, mm = m.groups()
            published = f"{y}-{int(mo):02d}-{int(d):02d} {int(hh):02d}:{mm}"
    return title, body, published


# ---------------------------------------------------------------- 采集：直连全文源

def collect_fulltext(source, settings, limit):
    items, seen = [], set()
    budget = settings.get("per_source_budget", 120)
    t_start = time.time()
    pattern = re.compile(source["link_pattern"])
    for page in source.get("list_pages", []):
        if time.time() - t_start > budget:
            print(f"  [预算] {source['name']} 超过 {budget}s，提前结束本源")
        try:
            list_html = http_get(page["url"], timeout=settings["request_timeout"])
        except Exception as exc:  # noqa: BLE001
            print(f"  [warn] 列表页失败 {page['url']}: {exc}", file=sys.stderr)
            continue
        links = []
        for m in pattern.finditer(list_html):
            url = (source.get("link_prefix") or "") + m.group(1)
            if url not in seen:
                seen.add(url)
                links.append(url)
        print(f"  · {page['channel']}: 发现 {len(links)} 条链接")
        for url in links:
            if len(items) >= limit:
                return items
            if time.time() - t_start > budget:
                print(f"  [预算] {source['name']} 正文采集超时，已得 {len(items)} 条，结束")
                return items
            try:
                html = http_get(url, timeout=settings["request_timeout"])
                title, body, published = extract_article(html, source.get("content_selectors"))
            except Exception as exc:  # noqa: BLE001
                print(f"  [warn] 正文失败 {url}: {exc}", file=sys.stderr)
                continue
            if not title or len(body) < settings["min_content_chars"]:
                continue
            items.append({
                "source_id": source["id"],
                "source": source["name"],
                "lang": source["lang"],
                "channel": page["channel"],
                "title": title,
                "url": url,
                "published": published,
                "content": body,
                "chars": len(body),
                "fulltext": True,
            })
            time.sleep(settings["request_delay"])
    return items


# ---------------------------------------------------------------- 采集：RSS 代理源

def rss2json(feed_url, count, timeout):
    api = ("https://api.rss2json.com/v1/api.json?rss_url="
           + urllib.parse.quote(feed_url, safe="") + f"&count={count}")
    txt = http_get(api, timeout=timeout, retries=2)
    return json.loads(txt)


def strip_html(s):
    if not s:
        return ""
    return clean_text(BeautifulSoup(s, "html.parser").get_text(" ", strip=True))


def collect_rss(source, settings, limit):
    items = []
    for feed in source.get("proxy_rss", []):
        try:
            data = rss2json(feed["url"], limit, settings["request_timeout"] + 8)
        except Exception as exc:  # noqa: BLE001
            print(f"  [warn] RSS 失败 {feed['url']}: {exc}", file=sys.stderr)
            continue
        if data.get("status") != "ok":
            print(f"  [warn] RSS 状态异常 {feed['channel']}: {data.get('message')}", file=sys.stderr)
            continue
        entries = data.get("items", [])
        print(f"  · {feed['channel']}: {len(entries)} 条")
        for it in entries[:limit]:
            title = strip_html(it.get("title", ""))
            desc = strip_html(it.get("description") or it.get("content") or "")
            if not title:
                continue
            items.append({
                "source_id": source["id"],
                "source": source["name"],
                "lang": source["lang"],
                "channel": feed["channel"],
                "title": title,
                "url": it.get("link", ""),
                "published": (it.get("pubDate") or "").replace("T", " ")[:16],
                "content": desc,
                "chars": len(desc),
                "fulltext": False,
                "paywalled": source["id"] in ("ft", "economist"),
            })
    return items


# ---------------------------------------------------------------- 分类与去重

def classify(item, categories):
    text = (item["title"] + " " + item["content"][:800]).lower()
    scores = {}
    for cat in categories:
        score = sum(2 if kw.lower() in item["title"].lower() else 1
                    for kw in cat["keywords"] if kw.lower() in text)
        if score:
            scores[cat["key"]] = score
    if not scores:
        return "other", "其他"
    key = max(scores, key=scores.get)
    label = next(c["label"] for c in categories if c["key"] == key)
    return key, label


def fingerprint(item):
    norm = re.sub(r"[\s\W]+", "", item["title"])[:40]
    return hashlib.md5((item["source_id"] + norm).encode()).hexdigest()[:16]


def filter_recent(items, days):
    """丢掉明显过期（站点首页残留旧文）的条目；无日期的保留。"""
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=days)
    out = []
    for it in items:
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", it.get("published") or "")
        if not m:
            out.append(it)
            continue
        try:
            if datetime.strptime(m.group(0), "%Y-%m-%d") >= cutoff:
                out.append(it)
        except ValueError:
            out.append(it)
    return out


def dedupe(items):
    out, seen_fp, seen_title = [], set(), set()
    for it in items:
        fp = fingerprint(it)
        tkey = re.sub(r"[\s\W]+", "", it["title"])[:28]
        if fp in seen_fp or tkey in seen_title:
            continue
        seen_fp.add(fp)
        seen_title.add(tkey)
        out.append(it)
    return out


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(SKILL_DIR, "data"))
    ap.add_argument("--only", default="")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    settings = cfg["settings"]
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    all_items, per_source = [], {}
    for source in cfg["sources"]:
        if only and source["id"] not in only:
            continue
        limit = args.limit or settings["max_articles_per_source"]
        print(f"\n[{source['name']}] 开始采集 ({'全文' if source['fulltext'] else 'RSS 摘要'})")
        t0 = time.time()
        if source["fulltext"]:
            items = collect_fulltext(source, settings, limit)
        else:
            items = collect_rss(source, settings, min(limit, 6))
        per_source[source["id"]] = len(items)
        print(f"  ✓ {len(items)} 条，耗时 {time.time() - t0:.1f}s")
        all_items.extend(items)

    all_items = dedupe(all_items)
    before = len(all_items)
    all_items = filter_recent(all_items, settings.get("max_age_days", 4))
    if len(all_items) != before:
        print(f"  时间过滤：{before} → {len(all_items)} 条")
    for it in all_items:
        key, label = classify(it, cfg["categories"])
        it["category"], it["category_label"] = key, label
        it["id"] = fingerprint(it)

    order = {c["key"]: i for i, c in enumerate(cfg["categories"] + [{"key": "other"}])}
    all_items.sort(key=lambda x: (order.get(x["category"], 99),
                                  "" if x["fulltext"] else "z",
                                  x["published"] or ""), reverse=False)

    cap = settings.get("max_articles_total", 72)
    if len(all_items) > cap:
        all_items = all_items[:cap]

    os.makedirs(args.out, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    payload = {
        "date": today,
        "generated_at": stamp,
        "total": len(all_items),
        "per_source": per_source,
        "articles": all_items,
    }
    day_path = os.path.join(args.out, f"{today}.json")
    with open(day_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    # 累积库（跨天保留，供检索）
    with open(os.path.join(args.out, "archive.jsonl"), "a", encoding="utf-8") as f:
        for it in all_items:
            f.write(json.dumps({**it, "date": today}, ensure_ascii=False) + "\n")

    print(f"\n合计 {len(all_items)} 条（去重后）→ {day_path}")
    print("分布:", json.dumps(per_source, ensure_ascii=False))


if __name__ == "__main__":
    main()
