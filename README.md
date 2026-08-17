# AI 赛事雷达

聚合全网 AI 竞赛 / 黑客松 / 创作赛信息的静态网页工具。

## 使用

```bash
python3 scripts/fetch_competehub.py 20   # 抓取 AI赛事通 前 20 页 -> data/competitions.json
python3 scripts/build_data.py           # 合并 data/manual.json 并去重 -> data/data.js
open index.html                          # 或 python3 -m http.server 8642
```

- `data/manual.json`：手工维护的官方重点赛事（`featured: true`），条目 schema 与抓取结果一致。
- 状态（报名中/进行中/已结束等）由前端按日期实时计算，无需重新构建。
