#!/usr/bin/env python3
"""Backcountry capture harness (headful Chromium under Xvfb).

www.backcountry.com sits behind an AWS WAF (CloudFront) that serves a
JavaScript challenge / image-puzzle CAPTCHA to plain HTTP clients and
headless browsers. The harness drives a real headful Chromium (persistent
profile, automation flags disabled) that passes the WAF challenge, and
records:

  - the as-rendered DOM HTML of each page
  - JSON/XHR API responses the page itself fires (search, category data)
  - a metadata sidecar (url, final url, title, len, ts)

Everything lands in scraped_data/captures/<key>.html / .json / .meta.json.

Usage:  xvfb-run -a python3 capture.py <plan.json>
        plan = [{"key": "...", "url": "...", "api": [substr...]}]
"""
import asyncio
import json
import os
import re
import sys
import time

from playwright.async_api import async_playwright

PROFILE = os.environ.get("BC_PROFILE", "/dev/shm/bc-profile")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captures")
os.makedirs(OUT, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")


def is_block(title, html):
    t = (title or "").lower()
    if "human verification" in t or "just a moment" in t or "access denied" in t:
        return True
    if html and "awswaf" in html[:8000] and "captcha" in html[:8000].lower():
        return True
    return False


async def capture_one(ctx, item, tries=4):
    key, url = item["key"], item["url"]
    api_want = item.get("api") or []
    meta_path = os.path.join(OUT, f"{key}.meta.json")
    html_path = os.path.join(OUT, f"{key}.html")
    apis_path = os.path.join(OUT, f"{key}.apis.json")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            old = json.load(f)
        if old.get("ok"):
            print(f"[skip] {key} already captured ok")
            return old

    for attempt in range(tries):
        page = await ctx.new_page()
        net = {}

        async def on_response(resp):
            try:
                ct = (resp.headers or {}).get("content-type", "")
                u = resp.url
                if resp.status != 200 or "json" not in ct:
                    return
                for pat in api_want:
                    if pat in u:
                        body = await resp.text()
                        net[u] = body[:6_000_000]
                        break
            except Exception:
                pass

        page.on("response", on_response)
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"[warn] {key}: goto: {str(e)[:90]}")
        await page.wait_for_timeout(5000)
        # scroll to trigger lazy grids
        try:
            await page.evaluate(
                "async () => { for (let y=0; y<document.body.scrollHeight; "
                "y+=1200) { window.scrollTo(0, y); await new Promise(r=>setTimeout(r,120)); } "
                "window.scrollTo(0,0); }")
        except Exception:
            pass
        await page.wait_for_timeout(2500)
        title = await page.title()
        html = await page.content()
        if is_block(title, html):
            print(f"[waf ] {key} attempt {attempt}: blocked (puzzle); retrying")
            try:
                btn = page.get_by_role("button", name="Begin")
                if await btn.count():
                    await btn.first.click(timeout=3000)
                    await page.wait_for_timeout(8000)
                    title = await page.title()
                    html = await page.content()
                    if not is_block(title, html):
                        pass
            except Exception:
                pass
            await page.close()
            await asyncio.sleep(4)
            continue
        meta = {
            "key": key, "url": url, "final_url": page.url, "title": title,
            "html_len": len(html), "ok": len(html) > 15000 and not is_block(title, html),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        with open(apis_path, "w", encoding="utf-8") as f:
            json.dump(net, f)
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=1)
        print(f"[done] {key}: len={len(html)} title={title[:60]!r} apis={len(net)}")
        await page.close()
        return meta
    return {"key": key, "url": url, "ok": False}


async def main():
    plan_path = sys.argv[1]
    with open(plan_path) as f:
        plan = json.load(f)
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            PROFILE, headless=False, user_agent=UA,
            viewport={"width": 1440, "height": 940},
            args=["--disable-blink-features=AutomationControlled"])
        # webdriver spoof
        for pg in ctx.pages:
            try:
                await pg.add_init_script(
                    "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
            except Exception:
                pass

        async def new_page_hook():
            pass

        ctx.on("page", lambda pg: asyncio.ensure_future(
            pg.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")))
        for item in plan:
            await capture_one(ctx, item)
            await asyncio.sleep(2.5)
        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
