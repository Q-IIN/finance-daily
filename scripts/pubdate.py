# -*- coding: utf-8 -*-
"""发布时间归一化。

各源给的格式完全不一样：新浪/东财是 `2026-11-10 09:30`，RSS 是 RFC822
`Sun, 08 Nov 2026 12:00:00 +0000`，还有带 Z 的 ISO。原先 fetch.py 直接
`[:16]` 截断，RSS 的日期就变成了 `Sun, 08 Nov 2026`，导致：

  · filter_recent 的正则匹配不上 → 时间过滤对 RSS 源完全失效
  · 字符串倒序时 "S"(0x53) > "2"(0x32) → 旧文章永远排在最前面

所以统一在这里转成 `YYYY-MM-DD HH:MM`（北京时间），供 fetch 和 build 共用。
"""
import os
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo(os.environ.get("FINANCE_DAILY_TZ", "Asia/Shanghai"))

_RFC = (
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M %z",
    "%a, %d %b %Y",
    "%d %b %Y %H:%M:%S %z",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
)


def norm_pubdate(value):
    """任意来源的发布时间 → 'YYYY-MM-DD HH:MM'（北京时间）；无法识别返回 ''。"""
    s = (value or "").strip()
    if not s:
        return ""

    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if dt.tzinfo:
                return dt.astimezone(TZ).strftime("%Y-%m-%d %H:%M")
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return s.replace("T", " ")[:16]

    try:
        dt = parsedate_to_datetime(s)
        if dt:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TZ)
            return dt.astimezone(TZ).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError, IndexError):
        pass

    for fmt in _RFC:
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TZ)
            return dt.astimezone(TZ).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue
    return ""


def norm_stamp(value):
    """把 'YYYY-MM-DD HH:MM:SS ±ZZZZ' 统一换算到业务时区，用于页脚“生成于”展示。"""
    s = (value or "").strip()
    if not s:
        return ""
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S %z").astimezone(TZ).strftime(
            "%Y-%m-%d %H:%M:%S %z")
    except ValueError:
        return s
