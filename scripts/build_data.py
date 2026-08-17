"""Merge manual.json + competitions.json (scraped), dedupe, emit data/data.js."""
import json
import re
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def norm(name: str) -> str:
    return re.sub(r"[\s　·・「」『』“”\"'（）()【】\[\]，,。.：:；;—\-|]+", "", name).lower()


def main():
    manual = json.loads((DATA / "manual.json").read_text())
    scraped = json.loads((DATA / "competitions.json").read_text())["competitions"]

    merged, keys = [], {}
    for c in manual + scraped:
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
    print(f"manual {len(manual)} + scraped {len(scraped)} -> {len(merged)} -> data/data.js")


if __name__ == "__main__":
    main()
