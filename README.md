# 财经日报 · Daily Finance Briefing

自动采集财经资讯并生成手机端 PWA 日报的无人值守流水线。

## 采集源

| 来源 | 深度 |
|---|---|
| 证券时报 / 中国证券报 / 第一财经 | 正文全文 |
| Reuters / FT 金融时报 / The Economist | 标题 + 摘要 + 原文链接 |
| 《财经》杂志（每周三） | 当期公开文章（全文/节选标记） |

## 工作原理

- GitHub Actions 定时触发（见 `.github/workflows/daily.yml`）：
  - **北京时间 07:00–22:00 每小时触发一次**，先跑 `scripts/should_run.py` 判重，
    距上次采集不足 3 小时就直接退出（几秒完成）
  - 这样即使某次 cron 被 GitHub 延迟/丢弃，最多 1 小时后也会自动补上
  - 周三额外采集《财经》杂志当期
- 采集结果渲染为静态站点，输出到 `docs/`
- `docs/health.json` 记录本次构建的 `build_id`、最新文章时间、今日新文条数、是否陈旧
- GitHub Pages 发布 `docs/` 为固定网址，手机可「添加到主屏幕」作为 PWA

## 时区

所有脚本统一使用 `Asia/Shanghai`（可用 `FINANCE_DAILY_TZ` 覆盖）。
GitHub Actions 的 runner 是 UTC，直接用 `datetime.now()` 会把北京 00:00–08:00
的批次写成前一天的文件名 —— 这是早报显示「昨天」的根因。

## 更新可见性

- 页面里注入 `build-id`，每 3 分钟（及切回前台时）带时间戳拉一次 `health.json`
- 发现线上 `build_id` 与页面不一致 → 右下角弹出「有新内容 / 刷新」提示
- Service Worker 对 HTML/JSON 采用网络优先（3.5s 超时），只在断网时用缓存兜底；
  `health.json` 永不缓存
- 数据陈旧时页面顶部会显示红色提示条，同时 Actions 会开 issue 提醒

## 手动触发

Actions → Daily Finance Briefing → Run workflow（强制全量，含杂志）。

## 本地运行

```bash
pip install beautifulsoup4
FINANCE_DAILY_OUT=docs python3 scripts/run_daily.py          # 日报
FINANCE_DAILY_OUT=docs python3 scripts/run_daily.py --magazine  # 杂志
FINANCE_DAILY_OUT=docs python3 scripts/run_daily.py --sync      # 采集并推送 GitHub
```

## 配置

`config/sources.json`：采集源、分类关键词、每源条数、总量上限、时间窗。

> 内容版权归原媒体所有，仅供个人阅读。Reuters/FT/经济学人经 RSS 代理获取摘要；
> 《财经》官网仅公开部分文章，部分为节选。
