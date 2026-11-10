#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把生成好的站点目录推送到 GitHub 仓库（走 Git Data API，不依赖 git 命令）。

用途：境内网络环境（本机 / 沙箱）能抓到境外机房抓不到的证券时报全文，
生成完整站点后，用本脚本覆盖 GitHub Pages 上的内容。

  export GH_TOKEN=xxx
  python3 sync_github.py --dir /workspace/finance-daily --repo Q-IIN/finance-daily

令牌读取顺序：环境变量 GH_TOKEN -> ~/.codebuddy/financial-news-daily/gh_token
"""
import argparse
import base64
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
TOKEN_FILE = os.path.expanduser("~/.codebuddy/financial-news-daily/gh_token")


def token():
    tok = os.environ.get("GH_TOKEN", "").strip()
    if not tok and os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, encoding="utf-8") as f:
            tok = f.read().strip()
    if not tok:
        sys.exit("缺少 GitHub 令牌：请设置 GH_TOKEN 或写入 " + TOKEN_FILE)
    return tok


def api(method, path, tok, payload=None, timeout=60):
    url = API + path if path.startswith("/") else path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "finance-daily-sync")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "ignore")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "ignore")[:300]
        raise SystemExit(f"GitHub API {method} {path} -> {exc.code}: {detail}")


def blob_sha(data):
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def collect_files(root):
    """返回 {仓库内路径: 绝对路径}，跳过无关文件。"""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in filenames:
            if name.startswith("."):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            out["docs/" + rel] = full
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="要推送的站点目录（内容会放到仓库 docs/ 下）")
    ap.add_argument("--repo", default="Q-IIN/finance-daily")
    ap.add_argument("--branch", default="master")
    ap.add_argument("--message", default="")
    ap.add_argument("--attempts", type=int, default=4, help="ref 冲突时的重试次数")
    args = ap.parse_args()

    tok = token()
    files = collect_files(args.dir)

    # Actions 的 git push 和本脚本会同时写同一个分支，PATCH ref 会偶发
    # 422 non-fast-forward。这里不是简单报错退出，而是重新取最新 head 再重放一次。
    for attempt in range(1, args.attempts + 1):
        try:
            done = push_once(args, tok, files)
            return done
        except SystemExit as exc:
            msg = str(exc)
            conflict = (" 422" in msg or " 409" in msg or "non-fast-forward" in msg
                        or "Update is not a fast forward" in msg)
            if not conflict or attempt == args.attempts:
                raise
            wait = 2 * attempt
            print(f"[warn] 第 {attempt} 次推送冲突，{wait}s 后重试（{msg[:120]}）", file=sys.stderr)
            time.sleep(wait)


def push_once(args, tok, files):
    ref = api("GET", f"/repos/{args.repo}/git/ref/heads/{args.branch}", tok)
    head = ref["object"]["sha"]
    commit = api("GET", f"/repos/{args.repo}/git/commits/{head}", tok)
    base_tree = commit["tree"]["sha"]
    remote = api("GET", f"/repos/{args.repo}/git/trees/{base_tree}?recursive=1", tok)
    remote_map = {n["path"]: n["sha"] for n in remote.get("tree", []) if n["type"] == "blob"}

    entries, changed = [], 0
    for path, full in sorted(files.items()):
        with open(full, "rb") as f:
            data = f.read()
        sha = blob_sha(data)
        if remote_map.get(path) == sha:
            continue
        blob = api("POST", f"/repos/{args.repo}/git/blobs", tok,
                   {"content": base64.b64encode(data).decode(), "encoding": "base64"})
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        changed += 1

    if not entries:
        print("· 内容与线上一致，无需推送")
        return True

    tree = api("POST", f"/repos/{args.repo}/git/trees", tok,
               {"base_tree": base_tree, "tree": entries})
    msg = args.message or f"chore: sync briefing {len(entries)} files"
    new_commit = api("POST", f"/repos/{args.repo}/git/commits", tok,
                     {"message": msg, "tree": tree["sha"], "parents": [head]})
    api("PATCH", f"/repos/{args.repo}/git/refs/heads/{args.branch}", tok,
        {"sha": new_commit["sha"], "force": False})
    print(f"✓ 已推送 {changed} 个文件 → {args.repo}@{new_commit['sha'][:7]}")
    return True


if __name__ == "__main__":
    main()
