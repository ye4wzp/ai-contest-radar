"""Merge manual.json + data/sources/*.json + previous data into data/data.js.

Accumulative: previously known competitions are kept while alive; entries more
than 14 days past their deadline/end move to data/archive.json.
"""
import json
import re
from datetime import date, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def norm(name: str) -> str:
    return re.sub(r"[\s　·・「」『』“”\"'（）()【】\[\]，,。.：:；;—\-|]+", "", name).lower()


def load_prev() -> list:
    f = DATA / "data.js"
    if not f.exists():
        return []
    raw = re.sub(r"^window\.__DATA__ = |;\s*$", "", f.read_text())
    prev = json.loads(raw)["competitions"]
    for c in prev:  # 跨源合并每次都从新鲜源重做，历史条目只保留自身来源
        c["sources"] = c["sources"][:1]
    return prev


def main():
    manual = json.loads((DATA / "manual.json").read_text())
    scraped = []
    for f in sorted((DATA / "sources").glob("*.json")):
        scraped += json.loads(f.read_text())["competitions"]
    prev = load_prev()

    cutoff = (date.today() - timedelta(days=14)).isoformat()

    def alive(c):
        final = c.get("end") or c.get("deadline")
        return c.get("featured") or not final or final >= cutoff

    merged, keys, ids = [], {}, set()
    for c in manual + [x for x in scraped + prev if alive(x)]:
        if c["id"] in ids:
            continue
        ids.add(c["id"])
        k = norm(c["name"])
        # 子串合并要求双方都够长，否则「黑客马拉松」这类泛称会吞掉所有含它的赛事
        dup = keys.get(k) or next(
            (keys[e] for e in keys if len(k) > 8 and len(e) > 8 and (k in e or e in k)), None
        )
        if dup:
            dup["sources"] += [s for s in c["sources"] if s not in dup["sources"]]
            continue
        keys[k] = c
        merged.append(c)

    # archive what fell out of the live set
    archive_f = DATA / "archive.json"
    archive = json.loads(archive_f.read_text()) if archive_f.exists() else []
    known = {c["id"] for c in archive}
    expired = [p for p in prev if not alive(p) and p["id"] not in known]
    if expired:
        archive_f.write_text(json.dumps(archive + expired, ensure_ascii=False, indent=1))

    out = {"updated": date.today().isoformat(), "competitions": merged}
    (DATA / "data.js").write_text(
        "window.__DATA__ = " + json.dumps(out, ensure_ascii=False) + ";\n"
    )
    print(f"manual {len(manual)} + sources {len(scraped)} + prev {len(prev)} "
          f"-> {len(merged)} live, +{len(expired)} archived")


if __name__ == "__main__":
    main()
