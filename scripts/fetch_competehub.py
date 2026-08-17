"""Scrape competehub.dev (AI赛事通) into data/competitions.json."""
import json
import re
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

BASE = "https://www.competehub.dev"
OUT = Path(__file__).resolve().parent.parent / "data" / "competitions.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
DELAY = 0.4

CN_DATE = re.compile(r"(20\d\d)年(\d{1,2})月(\d{1,2})日?")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def rsc_payload(html: str) -> str:
    chunks = re.findall(r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)', html)
    return "".join(json.loads(f'"{c}"') for c in chunks)


def json_objects(payload: str, marker: str):
    """Yield balanced JSON objects that follow each `marker` occurrence."""
    for m in re.finditer(re.escape(marker), payload):
        start = m.end()
        depth = 0
        for i in range(start, len(payload)):
            if payload[i] == "{":
                depth += 1
            elif payload[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        yield json.loads(payload[start : i + 1])
                    except json.JSONDecodeError:
                        pass
                    break


def iso_date(cn: str | None) -> str | None:
    if not cn:
        return None
    m = CN_DATE.search(cn)
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else None


def normalize(d: dict) -> dict:
    providers = [p["name"] for p in d.get("providers", []) if p.get("name")]
    prize = d.get("prize") or ""
    return {
        "id": d["id"],
        "name": d.get("title", "").strip(),
        "organizer": "、".join(providers) or None,
        "official_url": d.get("signupUrl") or None,
        "type": d.get("type") or d.get("displayCategory") or "其他",
        "tags": d.get("tags", []),
        "city": d.get("location") or d.get("displayCity") or "线上",
        "prize": None if prize in ("", "¥0", "$0") else prize,
        "start": iso_date(d.get("startDate")),
        "deadline": iso_date(d.get("closeDate")),
        "description": (d.get("introduction") or "")[:300],
        "sources": [{"name": "AI赛事通", "url": f"{BASE}/zh/competitions/{d['id']}"}],
    }


def main(pages: int = 20):
    ids: list[str] = []
    for page in range(1, pages + 1):
        payload = rsc_payload(fetch(f"{BASE}/zh/competitions?page={page}"))
        found = [c["id"] for c in json_objects(payload, '{"competition":') if c.get("id")]
        if not found:
            break
        ids.extend(x for x in found if x not in ids)
        print(f"page {page}: {len(found)} items", file=sys.stderr)
        time.sleep(DELAY)

    competitions, today = [], date.today().isoformat()
    for n, cid in enumerate(ids, 1):
        try:
            payload = rsc_payload(fetch(f"{BASE}/zh/competitions/{cid}"))
            detail = next(json_objects(payload, '"competition":'), None)
            if detail and detail.get("title"):
                c = normalize(detail)
                if not c["deadline"] or c["deadline"] >= today:  # keep active/undated only
                    competitions.append(c)
        except Exception as e:
            print(f"{cid}: {e}", file=sys.stderr)
        if n % 20 == 0:
            print(f"detail {n}/{len(ids)}, kept {len(competitions)}", file=sys.stderr)
        time.sleep(DELAY)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"updated": today, "competitions": competitions}, ensure_ascii=False, indent=1))
    print(f"wrote {len(competitions)} competitions -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
