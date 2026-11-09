"""Diagnostic round 5: jina with wait-for-selector / target-selector to bypass networkidle hang."""
import gzip
import re
import time
import urllib.error
import urllib.request

AID = "4327512"
TARGET = f"https://www.stcn.com/article/detail/{AID}.html"

VARIANTS = [
    ("wait-sel-html", {"X-Wait-For-Selector": ".article-content", "X-Return-Format": "html"}),
    ("target-text", {"X-Target-Selector": ".article-content", "X-Return-Format": "text"}),
    ("wait-sel-timeout", {"X-Wait-For-Selector": ".article-content", "X-Timeout": "40",
                          "X-Return-Format": "html"}),
]


def fetch(target, extra, timeout=100):
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


for name, extra in VARIANTS:
    time.sleep(2)
    try:
        st, body = fetch(TARGET, extra)
        text = " ".join(re.sub(r"<[^>]+>", " ", body).split())
        print(f"OK|{name}|status={st}|len={len(body)}|text={len(text)}|{text[:140]}")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = " ".join(exc.read().decode("utf-8", "ignore").split())[:160]
        except Exception:
            pass
        print(f"ERR|{name}|{exc.code}|{detail}")
    except Exception as exc:
        print(f"ERR|{name}|{type(exc).__name__}|{str(exc)[:110]}")
