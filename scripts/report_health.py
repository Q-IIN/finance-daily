#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取 docs/health.json，打印状态；数据陈旧时把 STALE=1 写进 $GITHUB_ENV，
供后续步骤决定是否开 issue 提醒。始终返回 0，不污染构建结果。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(ROOT, "docs", "health.json")

if not os.path.exists(path):
    print("没有 health.json，跳过")
    sys.exit(0)

with open(path, encoding="utf-8") as f:
    h = json.load(f)

print("health:", json.dumps(h, ensure_ascii=False))

if h.get("stale"):
    print(f"::warning title=日报数据陈旧::最新文章 {h.get('latest_published') or '无'}，"
          f"今日新文 {h.get('fresh_today', 0)} 条")
    with open(os.environ.get("GITHUB_ENV", os.devnull), "a", encoding="utf-8") as f:
        f.write("STALE=1\n")
else:
    print(f"✓ 数据新鲜：最新文章 {h.get('latest_published')}，今日 {h.get('fresh_today')} 条")
