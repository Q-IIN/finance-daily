"""Diagnostic round 7: check alternative CN finance sources reachable from GitHub runners."""
import gzip
import re
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

CANDIDATES = [
    ("cnstock-home", "https://www.cnstock.com/", "cnstock"),
    ("cnstock-list", "https://news.cnstock.com/news/sns_yw/index.html", "cnstock"),
    ("cls-telegraph", "https://www.cls.cn/nodeapi/telegraphList?app=CailianpressWeb&os=web&sv=7.7.5", "cls"),
    ("sina-roll", "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&num=20&page=1", "sina"),
    ("eastmoney-list", "https://finance.eastmoney.com/a/ccjdd.html", "eastmoney"),
]


def get(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip",
        "Referer": "https://www.cls.cn/",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return r.status, raw.decode("utf-8", "ignore")


for name, url, kind in CANDIDATES:
    try:
        st, body = get(url)
        links = len(re.findall(r'href="[^"]*(?:/a/|/news/|html)\d{4,}', body))
        ids = len(re.findall(r'\d{6,}', body))
        print(f"OK|{name}|status={st}|len={len(body)}|links={links}||{body.strip()[:100]}")
    except urllib.error.HTTPError as exc:
        print(f"ERR|{name}|{exc.code}")
    except Exception as exc:
        print(f"ERR|{name}|{type(exc).__name__}|{str(exc)[:80]}")
