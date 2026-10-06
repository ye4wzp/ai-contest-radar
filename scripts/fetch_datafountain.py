"""Fetch DataFountain competitions (public JSON API) into data/sources/datafountain.json.

列表按上线时间倒序，翻到整页都是一年前上线的为止；per_page 超过 30 左右会报 e50010。
每条是某个大赛下的一个赛题，名称拼上所属大赛（race.title）。源站不给报名截止，入门赛（常驻练习赛）不收。
"""
import json
from datetime import date, datetime, timedelta, timezone

from common import fetch, write_source

API = "https://www.datafountain.cn/api/competitions?page={page}&per_page=20"
CST = timezone(timedelta(hours=8))


def day(s: str | None) -> str | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(CST).date().isoformat()


def prize(s: str) -> str | None:
    if s.isdigit():  # 纯数字为人民币；个位两位数的是占位值
        return f"¥{int(s):,}" if int(s) > 100 else None
    return None if s in ("", "其他") else s  # 如「15.5万港元」


def normalize(c: dict) -> dict:
    race = c.get("race") or {}
    title = c["title"].strip()
    parent = (race.get("title") or "").strip()
    return {
        "id": f"datafountain-{c['id']}",
        "name": title if not parent or parent == title else f"{parent} - {title}",
        "organizer": "、".join(o["name"].strip() for o in c.get("organizers") or [] if o.get("role") == 1) or None,
        "official_url": f"https://www.datafountain.cn/competitions/{c['id']}",
        "type": "数据算法赛" if c.get("typeLabel") == "智能算法" else "创意应用赛",
        "tags": ["DataFountain"] + [t["nameCn"] for t in c.get("tags") or []],
        "city": None,
        "prize": prize((c.get("reward") or "").strip()),
        "start": day(c.get("startTime")),
        "deadline": None,
        "end": day(c.get("endTime")),
        "description": f"DataFountain 赛题，所属大赛：{parent}" if parent and parent != title else "DataFountain 赛题",
        "sources": [{"name": "DataFountain", "url": "https://www.datafountain.cn/competitions"}],
    }


def main():
    today = date.today()
    floor = (today - timedelta(days=365)).isoformat()
    comps = []
    for page in range(1, 20):
        items = json.loads(fetch(API.format(page=page)))["cmpt"]["competitions"]
        comps += [normalize(c) for c in items if c.get("typeLabel") != "入门赛"]
        if not items or all((day(c.get("startTime")) or "") < floor for c in items):
            break
    write_source("datafountain", [c for c in comps if (c["end"] or "") >= today.isoformat()])


if __name__ == "__main__":
    main()
