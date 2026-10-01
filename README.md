# AI 赛事雷达

聚合全网 AI 竞赛 / 黑客松 / 创作赛的静态网页工具。

**在线访问**：<https://ye4wzp.github.io/ai-contest-radar/>（GitHub Actions 每天北京时间 08:30 自动更新数据）

## 数据管线

```bash
pip install -r scripts/requirements.txt   # patchright；另需本机装有 Google Chrome
cd scripts
python3 fetch_competehub.py 50   # AI赛事通       -> data/sources/competehub.json
python3 fetch_tencent.py         # 腾讯云黑客松官网 -> data/sources/tencent.json
python3 fetch_mlh.py             # MLH 国际黑客松  -> data/sources/mlh.json
python3 fetch_mlcontests.py      # Kaggle/Zindi/Codabench/NeurIPS 竞赛赛道（经 mlcontests.com）-> data/sources/mlcontests.json
python3 fetch_devpost.py         # Devpost 上 AI 相关黑客松（公开 JSON API）-> data/sources/devpost.json
python3 fetch_aibetas.py         # 国内 AI 视频/AIGC 创作赛（aibetas.com 竞赛日历）-> data/sources/aibetas.json
cd .. && python3 scripts/build_data.py
# 累积合并全部源 + manual.json 并去重 -> data/data.js；结束超 14 天的赛事移入 data/archive.json
```

- AI赛事通站点有 Cloudflare 人机挑战：首次 403 时由 patchright 驾驭有头 Chrome 过一次挑战并复用 `cf_clearance`，
  其余请求仍走 urllib；CI 里跑在 `xvfb-run` 下。任一源抓取失败只告警，`build_data` 沿用上次已提交的源文件。
- 去重：名称相同/相近，或跨源官网链接相同即合并；AI赛事通是二手聚合（机翻名称、奖金折算成人民币），
  重复时以其他源的条目为主。Luma 活动只保留名称像比赛且与 AI 相关的，聚会/讲座/答疑等过滤掉。
- `data/manual.json`：手工维护的官方重点赛事（`featured: true`），条目 schema 与抓取结果一致。
- 日期字段：`start` 开始、`deadline` **报名截止**（拿不到就留空，MLH 不公布故一律留空；Devpost 取提交截止）、`end` 比赛结束；
  `signup`（`open`/`closed`/`upcoming`/`ended`）为源站自报的报名状态，优先于日期判定。
  AI赛事通的 `closeDate` 是比赛结束日而非报名截止，报名截止另从赛程正文解析。
- 状态（报名中/报名已结束/进行中/已结束等）由前端按上述字段实时计算，无需重新构建。
- 收藏：页面上点 ☆ 收藏比赛（存 localStorage），工具栏「★ 只看收藏」过滤。

## 飞书提醒

仓库 Settings → Secrets and variables → Actions 添加 `FEISHU_WEBHOOK`
（飞书群 → 设置 → 群机器人 → 添加「自定义机器人」，复制 webhook 地址）。
配置后每天自动推送：7 / 3 / 1 / 0 天截止的比赛清单，以及抓取失败告警。未配置则跳过。
