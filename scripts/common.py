"""Shared helpers for source fetchers."""
import json
import re
import tempfile
import threading
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
SOURCES = DATA / "sources"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

CN_DATE = re.compile(r"(20\d\d)年(\d{1,2})月(\d{1,2})日?")
ISO_DATE = re.compile(r"(20\d\d)-(\d{2})-(\d{2})")

_cf: dict = {}  # Cloudflare 放行凭据：{"Cookie": cf_clearance, "User-Agent": 过挑战时的浏览器 UA}
_cf_lock = threading.Lock()


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={**HEADERS, **_cf})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def fetch(url: str) -> str:
    """GET；遇 Cloudflare 挑战则用真实浏览器过一次，之后复用 cf_clearance（绑定 UA）。"""
    for retry in (False, True):
        try:
            return _get(url)
        except urllib.error.HTTPError as e:
            if retry or e.code != 403 or e.headers.get("cf-mitigated") != "challenge":
                raise
        stale = dict(_cf)
        with _cf_lock:  # 并发下只让第一个失败者去解，其余复用结果
            if _cf == stale:
                _cf.update(solve_challenge(url))


def solve_challenge(url: str, timeout: int = 60) -> dict:
    """patchright 驾驭系统 Chrome（CI 下跑在 xvfb 中），Turnstile 复选框需点击。"""
    from patchright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=tempfile.mkdtemp(), channel="chrome", headless=False, no_viewport=True)
        page = ctx.pages[0]
        page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        for _ in range(timeout // 2):
            try:
                if "__next_f" in page.content():
                    break
                box = page.locator('iframe[src*="challenges.cloudflare.com"]').first.bounding_box(timeout=1500)
                if box:
                    page.mouse.click(box["x"] + 30, box["y"] + box["height"] / 2)
            except Exception:
                pass  # 页面正在跳转或尚无 Turnstile，稍后再看
            page.wait_for_timeout(2000)
        else:
            ctx.close()
            raise RuntimeError(f"Cloudflare challenge not solved: {url}")
        ua = page.evaluate("navigator.userAgent")
        cookie = next(c["value"] for c in ctx.cookies() if c["name"] == "cf_clearance")
        ctx.close()
    return {"Cookie": f"cf_clearance={cookie}", "User-Agent": ua}


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
