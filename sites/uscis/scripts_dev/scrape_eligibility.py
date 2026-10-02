#!/usr/bin/env python3
"""Phase 5: harvest the Naturalization Eligibility Tool wizard tree.

The real wizard at
/citizenship-resource-center/learn-about-citizenship/naturalization-eligibility-tool-0
is a state machine: every page asks one question with radio options and a
Next button; terminal pages show an eligibility outcome. We walk every branch
(BFS, dedup by question), re-driving from the start for each edge, and store
the verbatim question texts, options, and outcome page texts.

Run:  python3.11 scrape_eligibility.py
"""
import json
import pathlib
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scraped_data" / "eligibility"
OUT.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
URL = ("https://www.uscis.gov/citizenship-resource-center/learn-about-citizenship/"
       "naturalization-eligibility-tool-0")
MAX_EDGES = 80
MAX_DEPTH = 9


def page_state(page) -> dict:
    """Current wizard page: question, options, whether it is an outcome page."""
    main_text = page.inner_text("main")
    options = page.eval_on_selector_all(
        "main label:visible",
        "els => els.map(e => e.textContent.trim()).filter(t => t && t.length < 400)")
    fixed = {"Next", "Back", "Start over", "Naturalization Eligibility Tool"}
    question = ""
    for line in main_text.split("\n"):
        line = line.strip()
        if line and line not in fixed and not any(o.startswith(line) for o in options):
            question = line
            break
    is_outcome = not options and bool(main_text.strip())
    return {"question": question, "options": options, "outcome": is_outcome, "text": main_text[:3000]}


def main() -> None:
    records = {"start": "", "states": {}, "edges": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(user_agent=UA, viewport={"width": 1366, "height": 1000})
        ctx.set_default_timeout(20000)
        page = ctx.new_page()

        def start_wizard():
            page.goto(URL, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(1100)
            page.get_by_text("Determine my eligibility").first.click()
            page.wait_for_timeout(1400)

        def click_option(opt: str) -> bool:
            try:
                loc = page.locator("main label", has_text=opt).first
                loc.click(timeout=8000)
                page.wait_for_timeout(450)
                page.get_by_role("button", name="Next").first.click(timeout=8000)
                page.wait_for_timeout(1300)
                return True
            except Exception:
                return False

        def drive(path) -> dict | None:
            start_wizard()
            for opt in path:
                if not click_option(opt):
                    return None
            return page_state(page)

        def state_key(st) -> str:
            return st["question"][:140] + "||" + "|".join(st["options"])[:140]

        seen = set()
        queue = [([], 0)]
        while queue and len(records["edges"]) < MAX_EDGES:
            path, depth = queue.pop(0)
            if depth > MAX_DEPTH:
                continue
            try:
                st = drive(path)
            except Exception as exc:
                print(f"  drive ERR at {path[:2]}...: {str(exc)[:80]}")
                continue
            if st is None:
                continue
            key = state_key(st)
            if not path:
                records["start"] = st["question"]
            if key in seen:
                continue
            seen.add(key)
            sid = f"s{len(records['states'])}"
            records["states"][sid] = st
            print(f"  state {sid}: Q='{st['question'][:60]}' opts={len(st['options'])} outcome={st['outcome']}")
            if not st["options"]:
                continue
            for opt in st["options"]:
                try:
                    nxt = drive(path + [opt])
                except Exception:
                    nxt = None
                if nxt is None:
                    continue
                records["edges"].append({
                    "from": key, "question": st["question"], "option": opt,
                    "to_state": state_key(nxt), "to_question": nxt["question"],
                    "to_outcome": nxt["outcome"],
                    "to_text": nxt["text"][:3000],
                })
                nxt_key = state_key(nxt)
                if not nxt["outcome"] and nxt_key not in seen:
                    queue.append((path + [opt], depth + 1))
                print(f"    edge#{len(records['edges'])}: --[{opt[:44]}]--> '{nxt['question'][:52]}'", flush=True)
                (OUT / "wizard.json").write_text(json.dumps(records, indent=1))
                time.sleep(0.15)
        (OUT / "wizard.json").write_text(json.dumps(records, indent=1))
        browser.close()
        print(f"states={len(records['states'])} edges={len(records['edges'])}")


if __name__ == "__main__":
    main()
