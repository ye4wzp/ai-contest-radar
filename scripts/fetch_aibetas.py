"""Fetch aibetas.com 竞赛日历（国内 AI 视频 / AIGC 创作赛）via WordPress REST into data/sources/aibetas.json.

ACF 字段给出主办方、奖金、类型、报名截止与官方报名链接；源站不提供开始与结束日期。
"""
import html
import json
import re
import urllib.error
from datetime import date

from common import fetch, write_source

API = "https://www.aibetas.com/wp-json/wp/v2/competition?per_page=100&page={page}&_fields=id,link,title,excerpt,acf"
TYPES = {"AI应用": "创意应用赛"}  # 其余（AI视频 / AI绘画 / 综合创作）统一归为创作赛


def text(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def normalize(d: dict) -> dict:
    acf = d.get("acf") or {}
    dl = acf.get("deadline") or ""
    kind = acf.get("competition_type") or ""
    return {
        "id": f"aibetas-{d['id']}",
        # 标题形如「XX大赛｜最高10万元，11月1日截止」，竖线后是站方摘要
        "name": re.split(r"[｜|]", text(d["title"]["rendered"]))[0].strip(),
        "organizer": acf.get("organizer") or None,
        "official_url": acf.get("registration_url") or d["link"],
        "type": TYPES.get(kind, "AI创作赛"),
        "tags": [t for t in (kind, "AIGC") if t],
        "city": None,
        "prize": acf.get("prize_info") or None,
        "start": None,
        "deadline": f"{dl[:4]}-{dl[4:6]}-{dl[6:8]}" if re.fullmatch(r"\d{8}", dl) else None,
        "end": None,
        "description": text(d.get("excerpt", {}).get("rendered"))[:300],
        "sources": [{"name": "AIBetas", "url": d["link"]}],
    }


def main():
    comps = []
    for page in range(1, 20):
        try:
            items = json.loads(fetch(API.format(page=page)))
        except urllib.error.HTTPError as e:
            if e.code == 400:  # WordPress 对越界页码返回 400
                break
            raise
        comps += [normalize(d) for d in items]
        if len(items) < 100:
            break
    today = date.today().isoformat()
    write_source("aibetas", [c for c in comps if c["deadline"] and c["deadline"] >= today])


if __name__ == "__main__":
    main()
