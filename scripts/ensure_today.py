#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打开即补跑守护：检测今天的日报是否已生成，没有就自动补采。

用于弥补 sandbox_agent 定时任务在沙箱休眠时不会真正执行的问题：
只要本会话被激活（你打开 WorkBuddy 并发起任意一次对话/刷新），
或手机上 PWA 后端有任意一次触发，就会补齐当天数据。

用法:
    python3 ensure_today.py            # 静默检测，缺则补
    python3 ensure_today.py --force    # 无视现状强制更新
    python3 ensure_today.py --status   # 只报告状态不动手
退出码: 0=已是今日(或已补齐成功)  2=刚补齐  1=采集失败
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("FINANCE_DAILY_OUT", "/workspace/finance-daily")
DATA = os.path.join(OUT, "data")
_TOKEN = os.path.expanduser("~/.codebuddy/financial-news-daily/gh_token")
TZ = ZoneInfo(os.environ.get("FINANCE_DAILY_TZ", "Asia/Shanghai"))


def today():
    return datetime.now(TZ).strftime("%Y-%m-%d")


def has_today():
    path = os.path.join(DATA, f"{today()}.json")
    return os.path.exists(path) and os.path.getsize(path) > 2000


def today_has_stcn():
    """本地当天数据是否包含证券时报（境外机房抓不到它，本地跑才有）。"""
    path = os.path.join(DATA, f"{today()}.json")
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return (d.get("per_source") or {}).get("stcn", 0) > 0
    except Exception:
        return False


def is_wednesday():
    return datetime.now(TZ).weekday() == 2  # Mon=0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    ok = has_today()
    stcn_ok = today_has_stcn()
    mag_today = os.path.exists(os.path.join(DATA, "magazine.json"))

    if args.status:
        print(f"今日({today()})日报: {'已有' if ok else '缺失'}"
              f"（证券时报 {'已含' if stcn_ok else '缺'}）")
        print(f"今日是否周三(需更新杂志): {'是' if is_wednesday() else '否'}")
        print(f"杂志数据: {'已有' if mag_today else '缺失'}")
        return 0 if ok else 1

    # 缺当天数据，或当天数据缺证券时报（境外机房生成的那份）时，都补跑一次本地全量
    need_daily = args.force or not ok or not stcn_ok
    need_mag = is_wednesday()  # 周三则顺带校验杂志

    if not need_daily and not need_mag:
        print(f"[ensure_today] {today()} 日报已存在，无需补跑")
        return 0

    if need_daily:
        print(f"[ensure_today] {today()} 日报缺失/强制更新，开始采集…")
        cmd = [sys.executable, os.path.join(SKILL_DIR, "scripts", "run_daily.py")]
        if os.environ.get("GH_TOKEN") or os.path.exists(_TOKEN):
            cmd.append("--sync")
        r = subprocess.run(cmd)
        if r.returncode != 0:
            print("[ensure_today] 日报采集失败", file=sys.stderr)
            return 1

    if need_mag:
        print("[ensure_today] 今日周三，顺带校验/更新《财经》杂志…")
        subprocess.run([sys.executable, os.path.join(SKILL_DIR, "scripts", "run_daily.py"),
                        "--magazine"])

    print("[ensure_today] 已补齐")
    return 2


if __name__ == "__main__":
    sys.exit(main())
