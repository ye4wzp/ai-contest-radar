"""Scrape competehub.dev (AI赛事通) into data/sources/competehub.json.

源站的 closeDate 是「比赛结束」而非报名截止：报名截止取自赛程正文，
拿不到时留空，另附源站自己的报名状态 signupStatus。
"""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from common import DATA, balanced_objects, fetch, iso_date, rsc_payload, write_source

BASE = "https://www.competehub.dev"
WORKERS = 6
SIGNUP = {1: "upcoming", 2: "open", 3: "closed", 4: "ended"}

_D = r"(?:(20\d\d)\s*年\s*)?(\d{1,2})\s*月\s*(\d{1,2})\s*日?|(20\d\d)[-/](\d{1,2})[-/](\d{1,2})"
REG_CLOSE = re.compile(r"报名(?:截止|结束)[^\n]{0,10}?[:：至到]\s*\**\s*(?:" + _D + ")")
REG_RANGE = re.compile(r"报名(?:时间|阶段|期间|日期)[^\n]{0,12}?[:：]?\s*\**\s*(?:" + _D +
                       r")\s*\**\s*[-—–~～至到]+\s*\**\s*(?:" + _D + ")")


def _iso(g: tuple, end: str) -> str | None:
    y, m, d = (g[0], g[1], g[2]) if g[1] else (g[3], g[4], g[5])
    if not m:
        return None
    if y:
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    for yy in (int(end[:4]), int(end[:4]) - 1):  # 无年份：取不晚于结束日的最近一年
        s = f"{yy:04d}-{int(m):02d}-{int(d):02d}"
        if s <= end:
            return s
    return None


def reg_deadline(text: str | None, end: str | None) -> str | None:
    """从赛程正文提取报名截止；越界（晚于结束日或早于一年前）视为误匹配。"""
    if not (text and end):
        return None
    floor = f"{int(end[:4]) - 1}{end[4:]}"
    for rx, off in ((REG_CLOSE, 0), (REG_RANGE, 6)):
        m = rx.search(text)
        if m:
            s = _iso(m.groups()[off:off + 6], end)
            if s and floor <= s <= end:
                return s
    return None


def normalize(d: dict) -> dict:
    providers = [p["name"] for p in d.get("providers", []) if p.get("name")]
    prize = d.get("prize") or ""
    detail = "\n\n".join(t.get("content", "") for t in d.get("tagContents", []))
    end = iso_date(d.get("closeDate"))
    return {
        "detail": detail[:2500] or None,
        "id": d["id"],
        "name": d.get("title", "").strip(),
        "organizer": "、".join(providers) or None,
        "official_url": d.get("signupUrl") or None,
        "type": d.get("type") or d.get("displayCategory") or "其他",
        "tags": d.get("tags", []),
        "city": d.get("location") or d.get("displayCity") or "线上",
        "prize": None if prize in ("", "¥0", "$0") else prize,
        "start": iso_date(d.get("startDate")),
        "deadline": reg_deadline(detail, end),
        "end": end,
        "signup": SIGNUP.get(d.get("signupStatus")),
        "description": (d.get("introduction") or "")[:300],
        "sources": [{"name": "AI赛事通", "url": f"{BASE}/zh/competitions/{d['id']}"}],
    }


def list_ids(pages: int) -> list[str]:
    ids = []
    for page in range(1, pages + 1):
        payload = rsc_payload(fetch(f"{BASE}/zh/competitions?page={page}"))
        found = [c["id"] for c in balanced_objects(payload, '{"competition":') if c.get("id")]
        if not found:
            break
        ids += found
    return ids


def known_ids() -> list[str]:
    """已收录条目一并复查，否则老条目的报名状态永远停在首次抓取那天。"""
    ids = []
    f = DATA / "sources" / "competehub.json"
    if f.exists():
        ids += [c["id"] for c in json.loads(f.read_text())["competitions"]]
    g = DATA / "data.js"
    if g.exists():
        raw = re.sub(r"^window\.__DATA__ = |;\s*$", "", g.read_text())
        ids += [c["id"] for c in json.loads(raw)["competitions"]
                if any(s["name"] == "AI赛事通" for s in c["sources"])]
    return ids


def detail(cid: str) -> dict | None:
    try:
        payload = rsc_payload(fetch(f"{BASE}/zh/competitions/{cid}"))
        # 同一 marker 也会命中 i18n 文案对象，按 title 甄别
        d = next((o for o in balanced_objects(payload, '"competition":') if o.get("title")), None)
        return normalize(d) if d else None
    except Exception as e:
        print(f"{cid}: {e}", file=sys.stderr)
        return None


def main(pages: int = 50):
    ids = list(dict.fromkeys(list_ids(pages) + known_ids()))
    print(f"ids: {len(ids)}", file=sys.stderr)
    with ThreadPoolExecutor(WORKERS) as ex:
        comps = [c for c in ex.map(detail, ids) if c]
    today = date.today().isoformat()
    write_source("competehub", [c for c in comps if not c["end"] or c["end"] >= today])


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 50)
