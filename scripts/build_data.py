"""Merge manual.json + new scrape + accumulated data, dedupe, emit data/data.js.

Accumulative: competitions from previous builds are kept until 14 days past
their deadline/end, so items falling off the scraped pages don't disappear.
"""
import json
import re
from datetime import date, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def norm(name: str) -> str:
    return re.sub(r"[\s　·・「」『』“”\"'（）()【】\[\]，,。.：:；;—\-|]+", "", name).lower()


def main():
    manual = json.loads((DATA / "manual.json").read_text())
    scraped = json.loads((DATA / "competitions.json").read_text())["competitions"]
    prev = []
    if (DATA / "data.js").exists():
        raw = re.sub(r"^window\.__DATA__ = |;\s*$", "", (DATA / "data.js").read_text())
        prev = json.loads(raw)["competitions"]

    cutoff = (date.today() - timedelta(days=14)).isoformat()

    def alive(c):
        final = c.get("end") or c.get("deadline")
        return c.get("featured") or not final or final >= cutoff

    merged, keys = [], {}
    for c in manual + scraped + [p for p in prev if alive(p)]:
        k = norm(c["name"])
        dup = keys.get(k) or next(
            (keys[e] for e in keys if len(k) > 8 and (k in e or e in k)), None
        )
        if dup:
            dup["sources"] += [s for s in c["sources"] if s not in dup["sources"]]
            continue
        keys[k] = c
        merged.append(c)

    out = {"updated": date.today().isoformat(), "competitions": merged}
    (DATA / "data.js").write_text(
        "window.__DATA__ = " + json.dumps(out, ensure_ascii=False) + ";\n"
    )
    print(f"manual {len(manual)} + scraped {len(scraped)} + prev {len(prev)} -> {len(merged)} -> data/data.js")


if __name__ == "__main__":
    main()
