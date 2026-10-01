"""Scrape mlcontests.com (Kaggle / Zindi / Codabench / NeurIPS 竞赛赛道等) into data/sources/mlcontests.json.

首页把全部赛事以 JSON 放在 data-competitions 属性里；其 deadline 是最终提交截止（即比赛结束），
registration-deadline 才是报名截止。
"""
import html
import json
import re
from datetime import date, datetime

from common import fetch, write_source

BASE = "https://mlcontests.com/"


def parse_date(s: str | None) -> str | None:
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime((s or "").strip(), fmt).date().isoformat()
        except ValueError:
            pass
    return None


def clean_url(url: str) -> str:
    return re.sub(r"[?&](ref|utm_\w+)=[^&]*", "", url).rstrip("?&")


def normalize(d: dict) -> dict:
    url = clean_url(d["url"])
    conf = d.get("conference")
    return {
        "id": "mlc-" + re.sub(r"\W+", "-", url.split("//")[-1]).strip("-"),
        "name": d["name"].strip(),
        "organizer": d.get("sponsor") or d.get("platform"),
        "official_url": url,
        "type": "数据算法赛",
        "tags": [t for t in (d.get("platform"), conf, "国际") if t],
        "city": "线上",
        "prize": d.get("prize") or None,
        "start": parse_date(d.get("launched")),
        "deadline": parse_date(d.get("registration-deadline")),
        "end": parse_date(d.get("deadline")),
        "description": " ".join(x for x in (
            f"{d['platform']} 平台赛事" if d.get("platform") else "",
            f"（{conf} 竞赛赛道）" if conf else "",
            d.get("note") or "") if x)[:300],
        "sources": [{"name": "ML Contests", "url": BASE}],
    }


def main():
    raw = re.search(r'data-competitions="([^"]+)"', fetch(BASE)).group(1)
    today = date.today().isoformat()
    comps = [normalize(d) for d in json.loads(html.unescape(raw)) if d.get("url") and d.get("name")]
    write_source("mlcontests", [c for c in comps if c["end"] and c["end"] >= today])


if __name__ == "__main__":
    main()
