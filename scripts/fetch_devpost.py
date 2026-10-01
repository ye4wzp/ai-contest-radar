"""Fetch Devpost open/upcoming hackathons (public JSON API) into data/sources/devpost.json.

只收 AI 相关的（主题含 Machine Learning/AI 或标题含 AI 关键词）。Devpost 没有单独的报名截止，
提交截止即最后参赛时间，记作 deadline。
"""
import json
import re
from datetime import datetime

from common import fetch, write_source

API = "https://devpost.com/api/hackathons?status[]={status}&page={page}"
AI = re.compile(r"\bAI\b|\bML\b|\bLLM|agent|machine learning|GPT|generative|人工智能", re.I)


def parse_period(s: str) -> tuple[str | None, str | None]:
    """'Aug 31 - Oct 23, 2026' / 'Oct 01 - 16, 2026' / 'Jul 18, 2026 - Jan 14, 2027' / 'Dec 31, 2026'"""
    left, _, right = s.partition(" - ")
    right = right or left
    if right[:1].isdigit():  # 同月区间省略了右侧月份
        right = f"{left.split()[0]} {right}"
    try:
        end = datetime.strptime(right, "%b %d, %Y").date()
        if "," in left:
            start = datetime.strptime(left, "%b %d, %Y").date()
        else:
            start = datetime.strptime(f"{left} {end.year}", "%b %d %Y").date()
            if start > end:
                start = start.replace(year=end.year - 1)
    except ValueError:
        return None, None
    return start.isoformat(), end.isoformat()


def prize(raw: str) -> str | None:
    text = re.sub(r"<[^>]+>", "", raw or "").strip()
    amount = re.sub(r"\D", "", text)
    # 不带币种符号的金额无法判断币种（多为印度卢比），宁缺毋滥
    if not amount or int(amount) == 0 or not re.match(r"\D", text):
        return None
    return text


def normalize(h: dict) -> dict:
    start, end = parse_period(h.get("submission_period_dates") or "")
    loc = (h.get("displayed_location") or {}).get("location") or ""
    return {
        "id": f"devpost-{h['id']}",
        "name": h["title"].strip(),
        "organizer": h.get("organization_name") or None,
        "official_url": h["url"],
        "type": "黑客松",
        "tags": ["Devpost", "国际"],
        "city": "线上" if loc.lower() == "online" else loc.strip() or None,
        "prize": prize(h.get("prize_amount")),
        "start": start,
        "deadline": end,
        "end": end,
        "signup": "open" if h.get("open_state") == "open" else "upcoming",
        "description": "Devpost 黑客松，主题：" + "、".join(t["name"] for t in h.get("themes", [])),
        "sources": [{"name": "Devpost", "url": "https://devpost.com/hackathons"}],
    }


def is_ai(h: dict) -> bool:
    return any(t["name"] == "Machine Learning/AI" for t in h.get("themes", [])) or bool(AI.search(h["title"]))


def main():
    comps, seen = [], set()
    for status in ("open", "upcoming"):
        for page in range(1, 50):
            hs = json.loads(fetch(API.format(status=status, page=page)))["hackathons"]
            if not hs:
                break
            for h in hs:
                if h["id"] not in seen and not h.get("invite_only") and is_ai(h):
                    seen.add(h["id"])
                    comps.append(normalize(h))
    write_source("devpost", comps)


if __name__ == "__main__":
    main()
