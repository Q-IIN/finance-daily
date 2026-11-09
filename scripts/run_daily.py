#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键更新：采集 -> 去重 -> 生成日报页面。供手动执行或定时任务调用。

  python3 run_daily.py              # 每日：六家媒体日报
  python3 run_daily.py --magazine   # 每周三：《财经》杂志当期
  python3 run_daily.py --all        # 两者都跑
"""
import subprocess
import sys
import os

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("FINANCE_DAILY_OUT", "/workspace/finance-daily")
DATA = os.path.join(OUT, "data")


def sh(cmd):
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(f"执行失败: {' '.join(cmd)}")


def main():
    do_mag = "--magazine" in sys.argv
    do_daily = "--magazine" not in sys.argv or "--all" in sys.argv

    if do_mag:
        print("=" * 56)
        print("Ⓜ 《财经》杂志当期采集")
        print("=" * 56)
        sh([sys.executable, os.path.join(SKILL_DIR, "scripts", "fetch_magazine.py"), "--out", DATA])
        sh([sys.executable, os.path.join(SKILL_DIR, "scripts", "build_magazine.py"), "--out", OUT])

    if do_daily:
        print("=" * 56)
        print("① 采集六家媒体")
        print("=" * 56)
        cmd = [sys.executable, os.path.join(SKILL_DIR, "scripts", "fetch.py"), "--out", DATA]
        for i, a in enumerate(sys.argv):
            if a == "--only" and i + 1 < len(sys.argv):
                cmd += ["--only", sys.argv[i + 1]]
        sh(cmd)
        print("=" * 56)
        print("② 生成日报")
        print("=" * 56)
        sh([sys.executable, os.path.join(SKILL_DIR, "scripts", "build.py"),
            "--data", DATA, "--out", OUT])

    print("\n✓ 完成。")


if __name__ == "__main__":
    main()
