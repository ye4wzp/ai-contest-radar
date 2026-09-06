# AI 赛事雷达

聚合全网 AI 竞赛 / 黑客松 / 创作赛的静态网页工具。

**在线访问**：<https://ye4wzp.github.io/ai-contest-radar/>（GitHub Actions 每天北京时间 08:30 自动更新数据）

## 数据管线

```bash
cd scripts
python3 fetch_competehub.py 50   # AI赛事通       -> data/sources/competehub.json
python3 fetch_tencent.py         # 腾讯云黑客松官网 -> data/sources/tencent.json
python3 fetch_mlh.py             # MLH 国际黑客松  -> data/sources/mlh.json
cd .. && python3 scripts/build_data.py
# 累积合并全部源 + manual.json 并去重 -> data/data.js；结束超 14 天的赛事移入 data/archive.json
```

- `data/manual.json`：手工维护的官方重点赛事（`featured: true`），条目 schema 与抓取结果一致。
- 日期字段：`start` 开始、`deadline` **报名截止**（拿不到就留空）、`end` 比赛结束；
  `signup`（`open`/`closed`/`upcoming`/`ended`）为源站自报的报名状态，优先于日期判定。
  AI赛事通的 `closeDate` 是比赛结束日而非报名截止，报名截止另从赛程正文解析。
- 状态（报名中/报名已结束/进行中/已结束等）由前端按上述字段实时计算，无需重新构建。
- 收藏：页面上点 ☆ 收藏比赛（存 localStorage），工具栏「★ 只看收藏」过滤。

## 飞书提醒

仓库 Settings → Secrets and variables → Actions 添加 `FEISHU_WEBHOOK`
（飞书群 → 设置 → 群机器人 → 添加「自定义机器人」，复制 webhook 地址）。
配置后每天自动推送：7 / 3 / 1 / 0 天截止的比赛清单，以及抓取失败告警。未配置则跳过。
