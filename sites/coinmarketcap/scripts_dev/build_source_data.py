#!/usr/bin/env python3
"""Materialize the tracked source_data/*.json snapshots from the raw
scraped_data/captures/ (gitignored) upstream captures.

Trim policy (declared in provenance.json):
  - coin chart series keep every k-th point of the captured series so the
    tracked snapshot stays reviewable — every kept value is an actual
    upstream point (t, price, volume, market cap); nothing is interpolated
    or synthesized. k is chosen per range so ~140 points remain.
  - OHLCV keeps full daily rows (no downsampling) for the captured windows
    (365d for the 30 headline coins, 90d for the rest).
  - the coin corpus is the upstream top-100 by market cap plus 19 curated
    coins that anchor the category/leaderboard pages; every row is a real
    upstream row.
  - upstream totals (e.g. category coin counts, total cryptos) are kept as
    context fields and rendered as context, never as the visible corpus
    size.

Run from sites/coinmarketcap:  python3.11 scripts_dev/build_source_data.py
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
CAPTURES = HERE / "scraped_data" / "captures"
OUT = HERE / "source_data"
OUT.mkdir(exist_ok=True)

HEADLINE = {
    "bitcoin", "ethereum", "tether", "bnb", "xrp", "usd-coin", "solana",
    "tron", "zcash", "hyperliquid", "dogecoin", "chainlink", "monero",
    "cardano", "stellar", "near-protocol", "litecoin", "avalanche",
    "shiba-inu", "aave", "uniswap", "pepe", "polkadot-new", "sui",
    "internet-computer", "ondo-finance", "cronos", "arbitrum",
    "pax-gold", "tether-gold",
}

CATEGORY_SLUGS = [
    "layer-1", "stablecoin", "memes", "defi", "ai-big-data", "gaming",
    "privacy", "collectibles-nfts", "oracles", "lending-borowing",
    "decentralized-exchange-dex-token", "real-world-assets-protocols",
    "storage",
]

CHART_KEEP = 140


def load(name: str):
    return json.loads((CAPTURES / name).read_text())


def dump(name: str, obj) -> None:
    (OUT / name).write_text(json.dumps(obj, indent=1, sort_keys=False) + "\n",
                            encoding="utf-8")


def next_data_of(page: str) -> dict:
    html = (CAPTURES / page).read_text(encoding="utf-8")
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>', html, re.S)
    return json.loads(m.group(1))


def usd_quote(row: dict) -> dict:
    for q in row.get("quotes", []):
        if q.get("name") == "USD":
            return q
    return row.get("quotes", [{}])[0]


def build_coins() -> list[dict]:
    corpus = load("corpus.json")
    coins = []
    for c in corpus:
        slug = c["slug"]
        det = load(f"detail_{slug}.json")["data"]
        stats = det.get("statistics", {})
        listing = None
        for name in ("listing_top100.json",):
            for row in load(name)["data"]["cryptoCurrencyList"]:
                if row["slug"] == slug:
                    listing = row
                    break
            if listing:
                break
        q = usd_quote(listing) if listing else {
            "price": stats.get("price"), "marketCap": stats.get("marketCap"),
            "volume24h": stats.get("volume24h"),
            "percentChange1h": stats.get("priceChangePercentage1h"),
            "percentChange24h": stats.get("priceChangePercentage24h"),
            "percentChange7d": stats.get("priceChangePercentage7d"),
            "percentChange30d": stats.get("priceChangePercentage30d"),
            "percentChange60d": stats.get("priceChangePercentage60d"),
            "percentChange90d": stats.get("priceChangePercentage90d"),
            "percentChange1y": stats.get("priceChangePercentage1y"),
            "ytdPriceChangePercentage": stats.get("ytdPriceChangePercentage"),
            "fullyDilluttedMarketCap": stats.get("fullyDilutedMarketCap"),
        }
        supply = det.get("supplyDetails", {}) or {}
        def supply_val(key):
            v = supply.get(key) or {}
            return v.get("value")
        coins.append({
            "id": det["id"],
            "slug": det["slug"],
            "name": det["name"],
            "symbol": det["symbol"],
            "category": det.get("category"),
            "status": det.get("status"),
            "rank": stats.get("rank") or (listing or {}).get("cmcRank"),
            "price": q.get("price"),
            "pct_1h": q.get("percentChange1h"),
            "pct_24h": q.get("percentChange24h"),
            "pct_7d": q.get("percentChange7d"),
            "pct_30d": q.get("percentChange30d"),
            "pct_60d": q.get("percentChange60d"),
            "pct_90d": q.get("percentChange90d"),
            "pct_1y": q.get("percentChange1y"),
            "pct_ytd": q.get("ytdPriceChangePercentage"),
            "pct_yesterday": stats.get("priceChangePercentageYesterday"),
            "volume_24h": q.get("volume24h"),
            "volume_7d": q.get("volume7d"),
            "volume_30d": q.get("volume30d"),
            "volume_reported_24h": stats.get("volume24hReported"),
            "cex_volume": det.get("cexVolume"),
            "dex_volume": det.get("dexVolume"),
            "market_cap": q.get("marketCap"),
            "fdv": q.get("fullyDilluttedMarketCap") or stats.get("fullyDilutedMarketCap"),
            "dominance": q.get("dominance"),
            "turnover": stats.get("turnover"),
            "roi": stats.get("roi"),
            "circulating_supply": (listing or {}).get("circulatingSupply", supply_val("circulatingSupply")),
            "self_reported_circulating": (listing or {}).get("selfReportedCirculatingSupply"),
            "total_supply": (listing or {}).get("totalSupply", supply_val("totalSupply")),
            "max_supply": (listing or {}).get("maxSupply", supply_val("maxSupply")),
            "supply_source": {k: (supply.get(k) or {}).get("sourceType")
                              for k in ("circulatingSupply", "totalSupply", "maxSupply")},
            "market_pair_count": (listing or {}).get("marketPairCount"),
            "date_added": det.get("dateAdded"),
            "date_launched": det.get("dateLaunched"),
            "launch_price": det.get("launchPrice"),
            "ath": (listing or {}).get("ath") or stats.get("highAllTime"),
            "ath_pct": stats.get("highAllTimeChangePercentage"),
            "ath_ts": stats.get("highAllTimeTimestamp"),
            "atl": (listing or {}).get("atl") or stats.get("lowAllTime"),
            "atl_pct": stats.get("lowAllTimeChangePercentage"),
            "atl_ts": stats.get("lowAllTimeTimestamp"),
            "high_24h": stats.get("high24h"),
            "low_24h": stats.get("low24h"),
            "high_7d": stats.get("high7d"),
            "low_7d": stats.get("low7d"),
            "high_30d": stats.get("high30d"),
            "low_30d": stats.get("low30d"),
            "high_52w": stats.get("high52w"),
            "low_52w": stats.get("low52w"),
            "open_yesterday": stats.get("openYesterday"),
            "close_yesterday": stats.get("closeYesterday"),
            "volume_rank": stats.get("volumeRank"),
            "watch_count": det.get("watchCount"),
            "watch_ranking": det.get("watchListRanking"),
            "description": det.get("description"),
            "urls": det.get("urls"),
            "tags": [{"slug": t.get("slug"), "name": t.get("name"),
                      "group": t.get("category")} for t in det.get("tags", [])],
            "platforms": det.get("platforms"),
            "holders": det.get("holders"),
            "similar": det.get("similarCoins"),
            "related": det.get("relatedCoins"),
            "ratings": det.get("cryptoRating"),
            "badges": (listing or {}).get("badges", []),
            "is_active": det.get("status") == "active",
            "last_updated": det.get("latestUpdateTime"),
        })
    coins.sort(key=lambda c: (c["rank"] is None, c["rank"] or 9999))
    dump("coins.json", coins)
    return coins


def build_charts(coins: list[dict]) -> None:
    series = {}
    for c in coins:
        slug = c["slug"]
        entry = {}
        for name in sorted(CAPTURES.glob(f"chart_*_{slug}.json")):
            rng = name.name.split("_")[1]
            data = json.loads(name.read_text()).get("data", {})
            raw = data.get("points") or {}
            if isinstance(raw, list):
                pts = {str(p["s"]): {"v": p["v"]} for p in raw if p.get("s")}
            else:
                pts = raw
            if not pts:
                continue
            keys = sorted(pts.keys(), key=int)
            step = max(1, len(keys) // CHART_KEEP)
            kept = [{"t": int(k), "p": pts[k]["v"][0],
                     "v": pts[k]["v"][1], "m": pts[k]["v"][2]}
                    for k in keys[::step]]
            if kept and keys[-1] != str(kept[-1]["t"]):
                k = keys[-1]
                kept.append({"t": int(k), "p": pts[k]["v"][0],
                             "v": pts[k]["v"][1], "m": pts[k]["v"][2]})
            entry[rng] = kept
        if entry:
            series[slug] = entry
    dump("charts.json", series)


def build_ohlcv(coins: list[dict]) -> None:
    rows = {}
    for c in coins:
        slug = c["slug"]
        for days in (365, 90):
            name = CAPTURES / f"ohlcv_{days}d_{slug}.json"
            if name.exists():
                d = json.loads(name.read_text())["data"]
                rows[slug] = [{
                    "date": q["timeOpen"][:10],
                    "open": q["quote"]["open"], "high": q["quote"]["high"],
                    "low": q["quote"]["low"], "close": q["quote"]["close"],
                    "volume": q["quote"]["volume"],
                    "market_cap": q["quote"]["marketCap"],
                    "supply": q["quote"]["circulatingSupply"],
                } for q in d["quotes"]]
                break
    dump("ohlcv.json", rows)


def build_market_pairs(coins: list[dict]) -> None:
    out = {}
    for c in coins:
        slug = c["slug"]
        name = CAPTURES / f"pairs_{slug}.json"
        if not name.exists():
            continue
        d = json.loads(name.read_text())["data"]
        out[slug] = {
            "num_pairs": d.get("numMarketPairs"),
            "pairs": [{
                "rank": p["rank"], "exchange": p["exchangeName"],
                "exchange_slug": p["exchangeSlug"], "pair": p["marketPair"],
                "category": p.get("category"), "price": p.get("price"),
                "volume_usd": p.get("volumeUsd"),
                "volume_pct": p.get("volumePercent"),
                "market_score": p.get("marketScore"),
                "market_reputation": p.get("marketReputation"),
                "fee_type": p.get("feeType"),
                "depth_neg_2": p.get("depthUsdNegativeTwo"),
                "depth_pos_2": p.get("depthUsdPositiveTwo"),
                "effective_liquidity": p.get("effectiveLiquidity"),
                "last_updated": p.get("lastUpdated"),
                "quote_symbol": p.get("quoteSymbol"),
                "market_url": p.get("marketUrl"),
            } for p in d.get("marketPairs", [])],
        }
    dump("market_pairs.json", out)


def build_exchanges() -> dict:
    out = {}
    for kind in ("spot", "dex", "derivatives"):
        nd = next_data_of(f"page_rankings_{kind}.html")
        init = nd["props"]["pageProps"]["initialData"]
        rows = []
        for e in init["exchanges"]:
            rows.append({
                "id": e["id"], "rank": e["rank"], "name": e["name"],
                "slug": e["slug"], "dex_status": e.get("dexStatus"),
                "score": e.get("score"), "traffic_score": e.get("trafficScore"),
                "visits": e.get("visits"), "liquidity": e.get("liquidity"),
                "maker_fee": e.get("makerFee"), "taker_fee": e.get("takerFee"),
                "spot_vol_24h": e.get("spotVol24h"),
                "derivatives_vol_24h": e.get("derivativesVol24h"),
                "derivatives_pairs": e.get("derivativesMarketPairs"),
                "derivatives_open_interest": e.get("derivativesOpenInterests"),
                "filtered_vol_24h": e.get("filteredTotalVol24h"),
                "total_vol_24h": e.get("totalVol24h"),
                "total_vol_7d": e.get("totalVol7d"),
                "total_vol_30d": e.get("totalVol30d"),
                "vol_chg_24h": e.get("totalVolChgPct24h"),
                "vol_chg_7d": e.get("totalVolChgPct7d"),
                "vol_chg_30d": e.get("totalVolChgPct30d"),
                "market_share_pct": e.get("marketSharePct"),
                "num_coins": e.get("numCoins"), "num_markets": e.get("numMarkets"),
                "date_launched": e.get("dateLaunched"),
                "fiats": e.get("fiats"), "countries": e.get("countries"),
                "status": e.get("status"), "por_audit": e.get("porAuditStatus"),
                "reserves": e.get("reservesAvailable"),
                "last_updated": e.get("lastUpdated"),
            })
        out[kind] = {"count": init["count"], "sort": init["sort"],
                     "direction": init["direction"], "exchanges": rows}

    details = {}
    for name in sorted(CAPTURES.glob("exdetail_*.json")):
        if name.name.endswith(".meta.json"):
            continue
        slug = name.name.removeprefix("exdetail_").removesuffix(".json")
        d = json.loads(name.read_text())["data"]
        details[slug] = {
            "id": d["id"], "name": d["name"], "slug": d["slug"],
            "description": d.get("description"),
            "maker_fee": d.get("makerFee"), "taker_fee": d.get("takerFee"),
            "dex_status": d.get("dexStatus"), "status": d.get("status"),
            "date_launched": d.get("dateLaunched"),
            "urls": d.get("urls"), "fiats": d.get("fiats"),
            "countries": d.get("countries"),
            "tags": [t.get("name") for t in (d.get("tags") or [])],
            "net_worth_usd": d.get("netWorthUsd"),
            "quote": d.get("quote", {}).get("2781"),
        }
    dump("exchanges.json", {"rankings": out, "details": details})

    pairs = {}
    for name in sorted(CAPTURES.glob("expairs_*.json")):
        if name.name.endswith(".meta.json"):
            continue
        slug = name.name.removeprefix("expairs_").removesuffix(".json")
        d = json.loads(name.read_text())["data"]
        pairs[slug] = [{
            "rank": p["rank"], "pair": p["marketPair"],
            "base": p.get("baseSymbol"), "quote": p.get("quoteSymbol"),
            "price": p.get("price"), "volume_24h": p.get("volumeUsd"),
            "volume_pct": p.get("volumePercent"),
            "liquidity_score": p.get("liquidityScore"),
            "market_url": p.get("marketUrl"), "category": p.get("category"),
            "last_updated": p.get("lastUpdated"),
        } for p in d.get("marketPairs", [])]
    dump("exchange_pairs.json", pairs)
    return out


def build_globals() -> None:
    gm = load("global_metrics_api.json")["data"]
    hist = load("global_metrics_hist90d.json")["data"]["quotes"]
    home = load("home_shared_data.json")
    page_latest = json.loads((CAPTURES / "global_metrics_latest.json").read_text())
    dump("global_metrics.json", {
        "latest": gm,
        "page_latest": page_latest,
        "historical_90d": [{
            "timestamp": q["timestamp"],
            "btc_dominance": q["btcDominance"],
            "eth_dominance": q["ethDominance"],
            "active_cryptos": q["activeCryptocurrencies"],
            "active_exchanges": q["activeExchanges"],
            "market_cap": q["quote"][0]["totalMarketCap"],
            "volume_24h": q["quote"][0]["totalVolume24H"],
        } for q in hist],
        "page_shared": home,
        "trending_top5": load("home_trending_top5.json"),
    })

    tr = load("trending_listing.json")["data"]
    dump("trending.json", {
        "total": tr["total"],
        "rows": [{
            "listing_rank": x.get("listingRank"), "symbol": x.get("tokenSymbol"),
            "name": x.get("tokenName"), "slug": x.get("slug"),
            "platform": x.get("platformName"), "price": x.get("priceUsd"),
            "pct_1h": x.get("pricePercentageChange1h"),
            "pct_24h": x.get("pricePercentageChange24h"),
            "pct_7d": x.get("pricePercentageChange7d"),
            "pct_30d": x.get("pricePercentageChange30d"),
            "volume_24h": x.get("volume24h"), "market_cap": x.get("marketCap"),
            "liquidity": x.get("liquidity"), "txs_24h": x.get("txs24h"),
            "age_ms": x.get("age"), "risk": x.get("riskLevel"),
        } for x in tr["list"]],
    })

    nd = next_data_of("page_upcoming.html")
    up = nd["props"]["pageProps"]["data"]
    dump("upcoming.json", {
        "total": up["totalSize"],
        "rows": up["upcoming"],
    })

    # most-viewed page: server-rendered table rows
    html = (CAPTURES / "page_most_viewed.html").read_text(encoding="utf-8")
    trs = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S)
    rows = []
    for tr in trs:
        links = re.findall(r'href="(/currencies/[^"]+)"', tr)
        cells = [" ".join(re.sub(r"<[^>]+>", " ", c).split())
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) >= 9 and links:
            rows.append({"rank": int(cells[1]), "slug": links[0].split("/")[2],
                         "name": cells[2].rsplit(" ", 2)[0], "price": cells[3],
                         "pct_24h": cells[4], "pct_7d": cells[5],
                         "pct_30d": cells[6], "market_cap": cells[7],
                         "volume_24h": cells[8]})
    dump("most_viewed.json", {"rows": rows})

    # historical snapshot
    html = (CAPTURES / "page_historical_20260927.html").read_text(encoding="utf-8")
    nd = next_data_of("page_historical_20260927.html")
    pp = nd["props"]["pageProps"]
    trs = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S)
    rows = []
    for tr in trs:
        cells = [" ".join(re.sub(r"<[^>]+>", " ", c).split())
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(cells) >= 10 and cells[0].isdigit():
            rows.append({
                "rank": int(cells[0]), "symbol": cells[2], "name": cells[1],
                "market_cap": cells[3], "price": cells[4],
                "circulating_supply": cells[5], "volume_24h": cells[6],
                "pct_1h": cells[7], "pct_24h": cells[8], "pct_7d": cells[9],
            })
    dump("snapshot_20260927.json", {
        "date": pp["dateWithHyphens"], "display": pp["displayDate"],
        "previous_week": pp["previousWeek"], "rows": rows,
    })


def build_categories() -> None:
    nd = next_data_of("page_categories_index.html")
    all_cats = nd["props"]["pageProps"]["data"]
    dump("categories_all.json", [{"sector_id": c["sectorId"], "name": c["name"]}
                                 for c in all_cats])

    cats = {}
    for tag in CATEGORY_SLUGS:
        nd = next_data_of(f"page_view_{tag}.html")
        pp = nd["props"]["pageProps"]
        sector = pp["sectorData"]
        lst = load(f"listing_cat_{tag}.json")["data"]
        cats[tag] = {
            "name": sector.get("name"),
            "sector_id": sector.get("sectorId"),
            "description": sector.get("description"),
            "stats": pp.get("statsData"),
            "market_cap": sector.get("marketCap"),
            "market_change": sector.get("marketChange"),
            "market_volume": sector.get("marketVolume"),
            "volume_change": sector.get("volumeChange"),
            "tokens_num": sector.get("tokensNum"),
            "upstream_total": lst.get("totalCount"),
            "top_coins": [{"id": c["id"], "slug": c["slug"], "name": c["name"],
                           "symbol": c["symbol"]}
                          for c in (sector.get("topCoinsList") or [])],
        }
    dump("categories.json", cats)


def build_content() -> None:
    # glossary
    nd = next_data_of("page_glossary_index.html")
    terms = nd["props"]["pageProps"]["glossaries"]
    dump("glossary_index.json", [
        {"title": t["title"], "slug": t["slug"], "excerpt": t["excerpt"],
         "difficulty": t.get("difficulty", {}).get("label")}
        for t in terms])

    full = {}
    for term in ("stablecoin", "blockchain", "smart-contract", "defi", "gas",
                 "hodl", "bear-market", "bull-market", "altcoin"):
        nd = next_data_of(f"page_glossary_{term}.html")
        g = nd["props"]["pageProps"]["glossary"]
        full[term] = {"title": g["title"], "slug": g["slug"],
                      "excerpt": g["excerpt"], "content": g["content"],
                      "difficulty": (g.get("difficulty") or {}).get("label")}
    dump("glossary_terms.json", full)

    # FAQ / methodology rendered text
    faq_text = (CAPTURES / "rendered_faq.txt").read_text(encoding="utf-8")
    i = faq_text.find("Frequently Asked Questions (FAQ)")
    dump("faq.json", {"rendered": faq_text[i:] if i >= 0 else faq_text})

    meth = (CAPTURES / "rendered_methodology.txt").read_text(encoding="utf-8")
    i = meth.find("Methodology")
    dump("methodology.json", {"rendered": meth[i:] if i >= 0 else meth})

    # auth modal captures (exact upstream strings)
    dump("auth_modals.json", {
        "login_modal": (CAPTURES / "rendered_login_modal.txt").read_text(),
        "login_error": (CAPTURES / "rendered_login_error.txt").read_text(),
        "signup_modal": (CAPTURES / "rendered_signup_modal.txt").read_text(),
        "signup_response": json.loads((CAPTURES / "rendered_signup_response.json").read_text()),
        "watchlist_prompt": (CAPTURES / "rendered_watchlist_prompt.txt").read_text(),
    })

    # converter popular conversions (captured API results)
    convs = {}
    for name in sorted(CAPTURES.glob("conv_*.json")):
        if name.name.endswith(".meta.json"):
            continue
        d = json.loads(name.read_text())["data"]
        convs[name.stem] = {
            "from_symbol": d["symbol"], "from_name": d["name"],
            "amount": d["amount"],
            "to_price": d["quote"][0]["price"],
            "to_symbol": d["quote"][0]["symbol"],
        }
    dump("conversions.json", convs)


def main() -> None:
    coins = build_coins()
    print(f"coins: {len(coins)}")
    build_charts(coins)
    build_ohlcv(coins)
    build_market_pairs(coins)
    build_exchanges()
    build_globals()
    build_categories()
    build_content()
    sizes = {p.name: p.stat().st_size for p in sorted(OUT.glob("*.json"))}
    for n, s in sizes.items():
        print(f"  {n}: {s/1024:.0f}KB")
    print(f"total: {sum(sizes.values())/1024/1024:.1f}MB")


if __name__ == "__main__":
    main()
