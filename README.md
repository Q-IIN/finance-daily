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
  - 每天 07:30 / 21:00（北京时间）采集六家媒体日报
  - 每周三 08:00 额外采集《财经》杂志当期
- 采集结果渲染为静态站点，输出到 `docs/`
- GitHub Pages 发布 `docs/` 为固定网址，手机可「添加到主屏幕」作为 PWA

## 手动触发

Actions → Daily Finance Briefing → Run workflow（会同时更新日报和杂志）。

## 本地运行

```bash
pip install beautifulsoup4
FINANCE_DAILY_OUT=docs python3 scripts/run_daily.py          # 日报
FINANCE_DAILY_OUT=docs python3 scripts/run_daily.py --magazine  # 杂志
```

## 配置

`config/sources.json`：采集源、分类关键词、每源条数、总量上限、时间窗。

> 内容版权归原媒体所有，仅供个人阅读。Reuters/FT/经济学人经 RSS 代理获取摘要；
> 《财经》官网仅公开部分文章，部分为节选。
