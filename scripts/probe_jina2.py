"""Diagnostic round 4: try variants to fetch an stcn detail page through r.jina.ai."""
import gzip
import re
import time
import urllib.error
import urllib.request

AID = "4327512"
VARIANTS = [
    ("html-https", f"https://www.stcn.com/article/detail/{AID}.html", {"X-Return-Format": "html"}),
    ("md-https", f"https://www.stcn.com/article/detail/{AID}.html", {"X-Return-Format": "markdown"}),
    ("html-http", f"http://www.stcn.com/article/detail/{AID}.html", {"X-Return-Format": "html"}),
    ("with-referer", f"https://www.stcn.com/article/detail/{AID}.html",
     {"X-Return-Format": "html", "X-Set-Referer": "https://www.stcn.com/"}),
    ("no-format", f"https://www.stcn.com/article/detail/{AID}.html", {}),
]


def fetch(target, extra, timeout=70):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Accept-Encoding": "gzip",
    }
    headers.update(extra)
    req = urllib.request.Request("https://r.jina.ai/" + target, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
        return r.status, data.decode("utf-8", "ignore")


for name, target, extra in VARIANTS:
    time.sleep(3)
    try:
        st, body = fetch(target, extra)
        text = " ".join(re.sub(r"<[^>]+>", " ", body).split())
        print(f"OK|{name}|status={st}|len={len(body)}|text={len(text)}|{text[:110]}")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = " ".join(exc.read().decode("utf-8", "ignore").split())[:150]
        except Exception:
            pass
        print(f"ERR|{name}|{exc.code}|{detail}")
    except Exception as exc:
        print(f"ERR|{name}|{type(exc).__name__}|{str(exc)[:100]}")
