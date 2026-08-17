"""Feishu webhook notifications. No FEISHU_WEBHOOK env -> silently skip.

Default: remind about competitions closing in 7/3/1/0 days.
--fail "msg": send a plain failure alert (used by CI on error).
"""
import json
import os
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
WEBHOOK = os.environ.get("FEISHU_WEBHOOK")
REMIND_DAYS = (7, 3, 1, 0)


def send(payload: dict):
    req = urllib.request.Request(
        WEBHOOK, json.dumps(payload).encode(), {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        body = json.loads(r.read())
    if body.get("code") not in (0, None):
        raise RuntimeError(f"feishu error: {body}")


def main():
    if not WEBHOOK:
        print("FEISHU_WEBHOOK not set, skip")
        return
    if len(sys.argv) > 2 and sys.argv[1] == "--fail":
        send({"msg_type": "text", "content": {"text": f"⚠️ AI 赛事雷达：{sys.argv[2]}"}})
        return

    raw = re.sub(r"^window\.__DATA__ = |;\s*$", "", (DATA / "data.js").read_text())
    comps = json.loads(raw)["competitions"]
    today = date.today()

    lines = []
    for c in sorted(comps, key=lambda x: x.get("deadline") or ""):
        if not c.get("deadline"):
            continue
        days = (date.fromisoformat(c["deadline"]) - today).days
        if days in REMIND_DAYS:
            when = "今天截止" if days == 0 else f"{days} 天后截止"
            lines.append([
                {"tag": "a", "text": c["name"], "href": c.get("official_url") or ""},
                {"tag": "text", "text": f" — {when}（{c['deadline']}）"},
            ])
    if not lines:
        print("no deadlines at D-7/3/1/0 today")
        return

    send({"msg_type": "post", "content": {"post": {"zh_cn": {
        "title": f"⏰ AI 赛事截止提醒 · {today.isoformat()}",
        "content": lines[:20],
    }}}})
    print(f"sent {len(lines)} reminders")


if __name__ == "__main__":
    main()
