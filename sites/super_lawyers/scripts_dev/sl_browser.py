"""Shared Playwright launcher for the superlawyers.com harvest.

superlawyers.com sits behind a Cloudflare JS challenge; a stock headless
Chromium gets "Just a moment...". Launching with the automation-controlled
blink feature disabled, a realistic UA, and webdriver undefined lets the
challenge auto-clear in a few seconds (observed 2026-09-26).

`goto_sl` waits until the challenge clears (or gives up after `tries`
polls) and returns whether the page looks rendered.
"""
from __future__ import annotations

import pathlib
import time

import httpx
from playwright.sync_api import sync_playwright

SITE = "https://www.superlawyers.com"
ATTORNEYS = "https://attorneys.superlawyers.com"
PROFILES = "https://profiles.superlawyers.com"
ANSWERS = "https://answers.superlawyers.com"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def launch():
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=[
        "--disable-blink-features=AutomationControlled", "--no-sandbox",
    ])
    ctx = browser.new_context(viewport={"width": 1366, "height": 768},
                              locale="en-US", user_agent=UA)
    ctx.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return pw, browser, ctx


def goto_sl(page, url, tries=16, settle_ms=1500):
    """Navigate and wait out the Cloudflare interstitial."""
    for attempt in range(3):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            time.sleep(3)
            continue
        for _ in range(tries):
            page.wait_for_timeout(settle_ms)
            title = page.title().lower()
            if "moment" not in title and "cloudflare" not in title \
                    and "performing security" not in title:
                return True
        time.sleep(2)
    return "moment" not in page.title().lower()


def fetch_bytes(url, referer="https://www.superlawyers.com/"):
    """Plain HTTP fetch for resolved asset URLs (never listing HTML)."""
    with httpx.Client(follow_redirects=True, timeout=45,
                      headers={"User-Agent": UA, "Referer": referer}) as cx:
        r = cx.get(url)
        r.raise_for_status()
        return r.content


def out_paths(site_dir, *parts):
    base = pathlib.Path(site_dir)
    return base.joinpath(*parts)
