"""Fetch 魔搭社区 ModelScope 活动 (public JSON API) into data/sources/modelscope.json.

活动列表混有沙龙、训练营、勋章申领等，只收 EventType == "competition" 的。
源站给报名起止（Unix 秒），比赛结束日多为 0（未填）；奖金多写在 BonusDesc 文案里。
"""
import json
from datetime import date, datetime, timedelta, timezone

from common import fetch, write_source

API = "https://www.modelscope.cn/api/v1/competitions?PageSize=50&PageNumber={page}"
CST = timezone(timedelta(hours=8))
TYPES = {"hackathon": "黑客松", "llm": "AI大模型赛", "application": "创意应用赛"}


def day(ts: int | None) -> str | None:
    return datetime.fromtimestamp(ts, CST).date().isoformat() if ts else None


def normalize(r: dict) -> dict:
    organizers = [o["Name"] for o in r.get("OrganizerInfo") or [] if o.get("Name")]
    bonus = r.get("Bonus") or 0
    desc = (r.get("BonusDesc") or "").strip()
    return {
        "id": f"modelscope-{r['Id']}",
        "name": r["Title"].strip(),
        "organizer": "、".join(organizers) or "魔搭社区",
        "official_url": f"https://modelscope.cn/events/{r['Id']}",
        "type": TYPES.get(r.get("Category"), "AI创作赛"),
        "tags": ["魔搭"],
        "city": r.get("EventLocation") or None,
        "prize": desc if desc.strip("0") else (f"¥{bonus:,}" if bonus else None),
        "start": day(r.get("SignUpStart")),
        "deadline": day(r.get("RegistrationDeadline")),
        "end": day(r.get("EndTime")),
        "description": (r.get("Brief") or "").strip()[:300],
        "sources": [{"name": "魔搭社区", "url": "https://modelscope.cn/active"}],
    }


def main():
    races = []
    for page in range(1, 20):
        items = json.loads(fetch(API.format(page=page)))["Data"]["Races"]
        races += [r for r in items if r.get("EventType") == "competition" and r.get("PublishStatus") == 1]
        if len(items) < 50:
            break
    today = date.today().isoformat()
    comps = [normalize(r) for r in races]
    write_source("modelscope", [c for c in comps if (c["end"] or c["deadline"] or today) >= today])


if __name__ == "__main__":
    main()
