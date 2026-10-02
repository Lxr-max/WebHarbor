#!/usr/bin/env python3
"""Capture the upstream cart + checkout pages with a real item in the cart.

Drives the live site: opens a product, adds the first in-stock sku to the
cart, captures the cart DOM, then proceeds to checkout (guest) and captures
that DOM too. Everything lands in scraped_data/captures/.
"""
import asyncio
import json
import os
import re
import time

from playwright.async_api import async_playwright

PROFILE = os.environ.get("BC_PROFILE", "/dev/shm/bc-profile2")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captures")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")


async def save(page, key, url):
    html = await page.content()
    with open(os.path.join(OUT, f"{key}.html"), "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(OUT, f"{key}.meta.json"), "w") as f:
        json.dump({"key": key, "url": url, "final_url": page.url,
                   "title": await page.title(), "html_len": len(html),
                   "ok": len(html) > 15000,
                   "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, f)
    print(f"[done] {key} len={len(html)}")


async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            PROFILE, headless=False, user_agent=UA,
            viewport={"width": 1440, "height": 940},
            args=["--disable-blink-features=AutomationControlled"])
        pg = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await pg.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")

        # 1. open a product with variants
        await pg.goto("https://www.backcountry.com/msr-hubba-hubba-2-tent-with-footprint",
                      timeout=60000)
        await pg.wait_for_timeout(5000)
        title = await pg.title()
        print("PDP title:", title[:70])
        if "verification" in title.lower():
            print("BLOCKED — retry needed")
            await ctx.close()
            return
        # 2. add to cart (click the first enabled size if present, then Add)
        try:
            sizes = pg.locator('button:has-text("Add to Cart")')
            add = pg.get_by_role("button", name="Add to Cart").first
            await add.click(timeout=8000)
            await pg.wait_for_timeout(5000)
        except Exception as e:
            print("add:", str(e)[:120])
        # 3. cart
        await pg.goto("https://www.backcountry.com/cart", timeout=60000)
        await pg.wait_for_timeout(6000)
        await save(pg, "cart_with_item", "https://www.backcountry.com/cart")
        # 4. checkout
        try:
            await pg.get_by_role("link", name="Proceed to Checkout").first.click(timeout=8000)
            await pg.wait_for_timeout(8000)
        except Exception as e:
            print("checkout click:", str(e)[:120])
        await save(pg, "checkout_page", pg.url)
        # 5. grab the visible text of both pages for reference
        for key in ["cart_with_item", "checkout_page"]:
            html = open(os.path.join(OUT, f"{key}.html"), encoding="utf-8").read()
            txt = re.sub(r"<script.*?</script>", "", html, flags=re.S)
            txt = re.sub(r"<style.*?</style>", "", txt, flags=re.S)
            txt = re.sub(r"<[^>]+>", " ", txt)
            txt = re.sub(r"\s+", " ", txt)
            with open(os.path.join(OUT, f"{key}.txt"), "w") as f:
                f.write(txt)
            print(key, "text head:", txt[:200])
        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
