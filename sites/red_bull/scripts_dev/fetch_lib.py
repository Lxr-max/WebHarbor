#!/usr/bin/env python3
"""Shared fetch helpers for the red_bull upstream scrape.

The upstream (www.redbull.com) is behind Akamai bot management: plain
curl/requests with default headers gets "Access Denied". Requests with a
coherent Safari browser header set are served the real pages. The JSON
content API (/v3/api/graphql/v1/...) works with the same header set.

All fetches go through fetch()/fetch_json() so every request uses the same
header contract and a single retry policy.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15")

HTML_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

JSON_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.redbull.com/us-en",
    "Connection": "keep-alive",
}

BASE = "https://www.redbull.com"
API = BASE + "/v3/api/graphql/v1"


def fetch(url: str, *, headers: dict | None = None, binary: bool = False,
          timeout: int = 40, retries: int = 3,
          min_bytes: int = 0) -> bytes:
    """Fetch a URL. If min_bytes is set and the response is smaller (the
    upstream occasionally serves a 8.5 KB client-render shell to rapid
    sequential requests), sleep and retry — the full SSR page comes back
    on the next attempt."""
    hdrs = dict(headers or HTML_HEADERS)
    last = None
    for attempt in range(retries + 2):
        req = urllib.request.Request(url, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            if min_bytes and len(body) < min_bytes and attempt < retries + 1:
                time.sleep(2.0 * (attempt + 1))
                continue
            return body
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (403, 401):
                raise          # bot-block: retrying will not help
            time.sleep(1.5 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch failed after {retries} tries: {url}: {last}")


def fetch_json(url: str, *, timeout: int = 40) -> dict:
    return json.loads(fetch(url, headers=JSON_HEADERS, timeout=timeout).decode("utf-8"))


def feed_page(kind: str, params: str, *, limit: int = 50, offset: int = 0,
              locale: str = "en-US%3Een-INT") -> dict:
    """One page of a /v3/feed/ query."""
    url = (f"{API}/v3/feed/{locale}?filter[type]={kind}&{params}"
           f"&rb3Locale=us-en&rb3Schema=v1:cardList"
           f"&page[limit]={limit}&page[offset]={offset}")
    return fetch_json(url)


def save(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, (bytes, bytearray)):
        path.write_bytes(obj)
    else:
        path.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
