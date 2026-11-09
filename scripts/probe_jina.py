"""Diagnostic: check whether r.jina.ai can pass stcn HTML through to a non-CN network."""
import gzip
import re
import time
import urllib.request


def jina(url, fmt="html", timeout=60):
    req = urllib.request.Request(
        "https://r.jina.ai/" + url,
        headers={
            "X-Return-Format": fmt,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "*/*",
            "Accept-Encoding": "gzip",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
        return r.status, data.decode("utf-8", "ignore")


def main():
    ids = []
    try:
        st, html = jina("https://www.stcn.com/article/list/yw.html")
        print(f"LIST status={st} len={len(html)}")
        ids = sorted(set(re.findall(r"article/detail/(\d+)\.html", html)))
        print("IDS:", ids[:5], "total", len(ids))
        print("article-content:", "article-content" in html)
    except Exception as exc:
        print("LIST ERR", type(exc).__name__, str(exc)[:200])

    for aid in ids[:2]:
        time.sleep(3)
        url = f"https://www.stcn.com/article/detail/{aid}.html"
        try:
            st, html = jina(url)
            text = re.sub(r"<[^>]+>", "", html)
            print(f"DETAIL {aid} status={st} len={len(html)} textlen={len(text)}")
            m = re.search(r'class="[^"]*(?:article-content|detail-content)[^"]*"', html)
            print("  container:", m.group(0) if m else "none")
            print("  head:", " ".join(text.split())[:150])
        except Exception as exc:
            print(f"DETAIL {aid} ERR", type(exc).__name__, str(exc)[:200])


if __name__ == "__main__":
    main()
