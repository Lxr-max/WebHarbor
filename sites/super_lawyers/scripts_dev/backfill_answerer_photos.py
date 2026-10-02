"""Backfill: for the Ask-a-Lawyer answers whose scrape missed the
answering attorney's headshot, re-visit the upstream answer page and
capture the answerer photo URL + full profile link. Updates
source_data/answers/<slug>.json in place (answerer.photo_url only).

Run from sites/super_lawyers/scripts_dev/ with the agent_demo venv.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sl_browser import goto_sl, launch  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE.parent / "source_data" / "answers"


def main() -> None:
    todo = []
    for path in sorted(SRC.glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        if not (rec.get("answerer") or {}).get("photo_url"):
            todo.append((path, rec))
    print(f"[backfill] {len(todo)} answers missing answerer photos")
    if not todo:
        return
    pw, browser, ctx = launch()
    page = ctx.new_page()
    fixed = 0
    for path, rec in todo:
        try:
            goto_sl(page, rec["url"])
            html = page.content()
        except Exception as exc:  # noqa: BLE001
            print(f"  [fail] {path.stem[:60]}: {exc}")
            continue
        i, j = html.find("<main"), html.find("</main>")
        main = html[i:j] if 0 <= i < j else html
        m = re.search(
            r'<img[^>]+src="(https://cdn\.superlawyers\.com[^"]+'
            r'attorney_by_uuid[^"]+)"', main)
        if not m:
            # some pages put the avatar before the Answered-by block
            m = re.search(
                r'<img[^>]+src="(https://cdn\.superlawyers\.com/image/upload'
                r'[^"]+)"[^>]*alt="([^"]+)"', main)
        if not m:
            print(f"  [miss] {path.stem[:70]}")
            continue
        rec.setdefault("answerer", {})["photo_url"] = m.group(1)
        path.write_text(json.dumps(rec, indent=1, sort_keys=True,
                                   ensure_ascii=False) + "\n")
        fixed += 1
        print(f"  [ok] {path.stem[:60]}")
    browser.close()
    pw.stop()
    print(f"[backfill] fixed {fixed}/{len(todo)}")


if __name__ == "__main__":
    main()
