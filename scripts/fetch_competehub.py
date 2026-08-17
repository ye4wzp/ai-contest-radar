"""Scrape competehub.dev (AI赛事通) into data/sources/competehub.json."""
import sys
import time
from datetime import date

from common import balanced_objects, fetch, iso_date, rsc_payload, write_source

BASE = "https://www.competehub.dev"
DELAY = 0.4


def normalize(d: dict) -> dict:
    providers = [p["name"] for p in d.get("providers", []) if p.get("name")]
    prize = d.get("prize") or ""
    detail = "\n\n".join(t.get("content", "") for t in d.get("tagContents", []))[:2500]
    return {
        "detail": detail or None,
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


def main(pages: int = 50):
    ids: list[str] = []
    for page in range(1, pages + 1):
        payload = rsc_payload(fetch(f"{BASE}/zh/competitions?page={page}"))
        found = [c["id"] for c in balanced_objects(payload, '{"competition":') if c.get("id")]
        if not found:
            break
        ids.extend(x for x in found if x not in ids)
        time.sleep(DELAY)
    print(f"list pages: {page}, ids: {len(ids)}", file=sys.stderr)

    comps, today = [], date.today().isoformat()
    for n, cid in enumerate(ids, 1):
        try:
            payload = rsc_payload(fetch(f"{BASE}/zh/competitions/{cid}"))
            detail = next(balanced_objects(payload, '"competition":'), None)
            if detail and detail.get("title"):
                c = normalize(detail)
                if not c["deadline"] or c["deadline"] >= today:
                    comps.append(c)
        except Exception as e:
            print(f"{cid}: {e}", file=sys.stderr)
        if n % 50 == 0:
            print(f"detail {n}/{len(ids)}, kept {len(comps)}", file=sys.stderr)
        time.sleep(DELAY)

    write_source("competehub", comps)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 50)
