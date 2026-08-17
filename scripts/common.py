"""Shared helpers for source fetchers."""
import json
import re
import urllib.request
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
SOURCES = DATA / "sources"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

CN_DATE = re.compile(r"(20\d\d)年(\d{1,2})月(\d{1,2})日?")
ISO_DATE = re.compile(r"(20\d\d)-(\d{2})-(\d{2})")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def rsc_payload(html: str) -> str:
    """Join Next.js App Router streamed flight chunks."""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)', html)
    return "".join(json.loads(f'"{c}"') for c in chunks)


def balanced_objects(payload: str, marker: str):
    """Yield balanced JSON objects starting at each `marker` occurrence's end."""
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


def iso_date(s: str | None) -> str | None:
    if not s:
        return None
    m = CN_DATE.search(s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = ISO_DATE.search(s)
    return m.group(0) if m else None


def write_source(name: str, competitions: list):
    SOURCES.mkdir(parents=True, exist_ok=True)
    out = {"updated": date.today().isoformat(), "competitions": competitions}
    (SOURCES / f"{name}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"{name}: {len(competitions)} competitions")
