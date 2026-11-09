"""Diagnostic round 6: test every remaining candidate channel for stcn full text."""
import gzip
import re
import time
import urllib.error
import urllib.parse
import urllib.request

AID = "4327512"
DETAIL = f"https://www.stcn.com/article/detail/{AID}.html"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


def get(url, headers=None, timeout=60):
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9", "Accept-Encoding": "gzip"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return r.status, raw.decode("utf-8", "ignore")


def report(name, fn):
    try:
        st, body = fn()
        text = " ".join(re.sub(r"<[^>]+>", " ", body).split())
        hit = "article-content" in body
        print(f"OK|{name}|status={st}|len={len(body)}|text={len(text)}|sel={hit}|{text[:110]}")
    except urllib.error.HTTPError as exc:
        try:
            d = " ".join(exc.read().decode("utf-8", "ignore").split())[:120]
        except Exception:
            d = ""
        print(f"ERR|{name}|{exc.code}|{d}")
    except Exception as exc:
        print(f"ERR|{name}|{type(exc).__name__}|{str(exc)[:110]}")


# 1. Google Translate proxy (zh-CN -> zh-TW keeps Chinese text, converts script)
tg = "https://www-stcn-com.translate.goog/article/detail/%s.html?_x_tr_sl=zh-CN&_x_tr_tl=zh-TW&_x_tr_hl=zh-CN" % AID
report("translate-goog-tw", lambda: get(tg))

# 2. jina with wait-for-selector + long timeout
report("jina-wait-60", lambda: get(
    "https://r.jina.ai/" + DETAIL,
    {"X-Wait-For-Selector": ".article-content", "X-Timeout": "60", "X-Return-Format": "html"}, 110))

# 3. microlink generic renderer
ml = "https://api.microlink.io/?url=" + urllib.parse.quote(DETAIL, safe="") + "&meta=false&data.content.selector=" + urllib.parse.quote(".article-content", safe="")
report("microlink", lambda: get(ml, timeout=70))

# 4. stcn list via jina (confirm still works, count links)
report("jina-list", lambda: get("https://r.jina.ai/https://www.stcn.com/article/list/yw.html",
                                {"X-Return-Format": "html"}, 90))
