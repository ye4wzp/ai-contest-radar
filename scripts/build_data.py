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


def url_key(url: str | None) -> str | None:
    if not url:
        return None
    url = re.sub(r"[?&](ref|utm_\w+|live_from)=[^&]*", "", url.lower())
    return re.sub(r"^https?://(www\.)?|[/?&#]+$", "", url)


CONTEST = re.compile(r"黑客|hack|马拉松|挑战|竞赛|比赛|大赛|buildathon|ideathon|创客松|jam", re.I)
NOT_CONTEST = re.compile(
    r"办公时间|office hours|聚会|见面会|交流会|讲座|分享会|研讨会|招待|派对|欢乐时光|happy hour|"
    r"networking|meetup|演示日|演示之夜|demo day|获奖者展示|共工作|协同办公|圆桌|"
    r"沙龙|训练营|实战营|创作营|集训营|论坛|会议", re.I)
# AI赛事通把 Agent 机翻成「代理」「特工」
AI = re.compile(r"AI|人工智能|智能|大模型|代理|特工|[Aa]gent|LLM|GPT|机器学习|深度学习|模型|具身|Qwen|千问")


def off_topic(c: dict) -> bool:
    """AI赛事通混有聚会、训练营和与 AI 无关的创业赛、Web3/CTF 赛，其他源本身已按 AI 筛过。"""
    if c["sources"][0]["name"] != "AI赛事通":
        return False
    name, url = c["name"], c.get("official_url") or ""
    ai = "机器学习/AI" in c.get("tags", []) or AI.search(name)
    # Luma 上大量是聚会、讲座、答疑，只留名称像比赛且与 AI 相关的
    if "luma.com" in url:
        return not (CONTEST.search(name) and not NOT_CONTEST.search(name) and ai)
    if NOT_CONTEST.search(name) and not CONTEST.search(name):
        return True
    return not (ai or "lablab.ai" in url or AI.search(c.get("description") or ""))


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
    # AI赛事通是二手聚合（机翻名称、奖金折成人民币、多无报名截止），与其他源重复时让其他源的条目做主；
    # 魔搭常转载天池等平台的赛事且不给结束日，也排在一手源之后
    last = ("modelscope", "competehub")
    for f in sorted((DATA / "sources").glob("*.json"),
                    key=lambda f: (last.index(f.stem) if f.stem in last else -1, f.stem)):
        scraped += json.loads(f.read_text())["competitions"]
    prev = load_prev()

    cutoff = (date.today() - timedelta(days=14)).isoformat()

    def alive(c):
        final = c.get("end") or c.get("deadline")
        return c.get("featured") or not final or final >= cutoff

    merged, keys, urls, ids = [], {}, {}, set()
    for c in manual + [x for x in scraped + prev if alive(x) and not off_topic(x)]:
        if c["id"] in ids:
            continue
        ids.add(c["id"])
        k, u = norm(c["name"]), url_key(c.get("official_url"))
        # 子串合并要求双方都够长，否则「黑客马拉松」这类泛称会吞掉所有含它的赛事
        dup = keys.get(k) or next(
            (keys[e] for e in keys if len(k) > 8 and len(e) > 8 and (k in e or e in k)), None
        )
        # 名称跨语言对不上时按官网链接合并；同源内不按链接合并（腾讯多场赛事共用官网首页）
        if not dup and u in urls and urls[u]["sources"][0]["name"] != c["sources"][0]["name"]:
            dup = urls[u]
        if dup:
            dup["sources"] += [s for s in c["sources"] if s not in dup["sources"]]
            continue
        keys[k] = c
        if u:
            urls.setdefault(u, c)
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
