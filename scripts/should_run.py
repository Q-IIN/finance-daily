#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""幂等闸门：决定这次触发要不要真的去采集。

背景：GitHub Actions 的 schedule 在高峰期会延迟几十分钟甚至直接丢弃，
单靠「一天两个 cron」必然出现漏跑。改成「每小时触发一次 + 本脚本判重」，
漏跑最多 1 小时后被下一次自动补上，而多余的触发只花几秒就退出。

输出（写入 $GITHUB_OUTPUT）：
    run=true|false        是否执行日报采集
    magazine=true|false   是否顺带更新《财经》杂志

退出码恒为 0，避免把「不需要跑」当成失败。
"""
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo(os.environ.get("FINANCE_DAILY_TZ", "Asia/Shanghai"))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "docs", "data")
MIN_INTERVAL_HOURS = float(os.environ.get("FINANCE_DAILY_MIN_INTERVAL", "3"))


def out(**kv):
    line = "\n".join(f"{k}={str(v).lower() if isinstance(v, bool) else v}" for k, v in kv.items())
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    print(line)


def parse(ts):
    """generated_at 形如 '2026-11-10 12:43:57 +0800'。"""
    try:
        return datetime.strptime(ts.strip(), "%Y-%m-%d %H:%M:%S %z")
    except Exception:  # noqa: BLE001
        return None


def main():
    now = datetime.now(TZ)
    today = now.strftime("%Y-%m-%d")
    forced = os.environ.get("FORCE_RUN", "").lower() in ("1", "true", "yes")

    if forced:
        out(run=True, magazine=True, reason="workflow_dispatch 强制全量")
        return 0

    day_json = os.path.join(DATA, f"{today}.json")
    if not os.path.exists(day_json):
        out(run=True, magazine=now.weekday() == 2, reason=f"缺少 {today}.json")
        return 0

    try:
        with open(day_json, encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as exc:  # noqa: BLE001
        out(run=True, magazine=False, reason=f"{today}.json 解析失败: {exc}")
        return 0

    gen = parse(payload.get("generated_at", ""))
    if gen is None:
        out(run=True, magazine=False, reason="generated_at 无法解析")
        return 0

    age_h = (now - gen).total_seconds() / 3600.0
    if age_h < MIN_INTERVAL_HOURS:
        out(run=False, magazine=False,
            reason=f"距上次采集 {age_h:.1f}h < {MIN_INTERVAL_HOURS}h，跳过")
        return 0

    # 杂志：周三且本地杂志数据超过 5 天没更新才跑
    want_mag = False
    if now.weekday() == 2:
        mag = os.path.join(DATA, "magazine.json")
        if not os.path.exists(mag):
            want_mag = True
        else:
            mtime = datetime.fromtimestamp(os.path.getmtime(mag), TZ)
            want_mag = (now - mtime).days >= 5

    out(run=True, magazine=want_mag, reason=f"距上次采集 {age_h:.1f}h，需要刷新")
    return 0


if __name__ == "__main__":
    sys.exit(main())
