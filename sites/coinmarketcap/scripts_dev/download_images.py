#!/usr/bin/env python3
"""Download every managed image for the coinmarketcap mirror from its exact
upstream URL and record path/bytes/sha256/source_url in the tracked
asset_inventory.json.

Sources (all real upstream, fetched 2026-09-29/30 UTC):
  - s2.coinmarketcap.com/static/img/coins/{64x64,200x200}/<id>.png  coin logos
  - s2.coinmarketcap.com/static/img/exchanges/64x64/<id>.png        exchange logos
  - s3.coinmarketcap.com/generated/sparklines/web/7d/2781/<id>.svg  table sparkline (needs Referer)
  - s2.coinmarketcap.com/static/cloud/img/menu/*.svg                 nav/menu icons
  - s2.coinmarketcap.com/static/cloud/img/coinmarketcap_1.svg        site logo
  - coinmarketcap.com/favicon.ico / apple-touch-icon.png             brand icons

Run from sites/coinmarketcap:  python3.11 scripts_dev/download_images.py
"""
import hashlib
import json
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent.parent
CAPTURES = HERE / "scraped_data" / "captures"
IMAGES = HERE / "static" / "images" / "upstream"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
S2 = "https://s2.coinmarketcap.com"
S3 = "https://s3.coinmarketcap.com"
SITE = "https://coinmarketcap.com"

HEADLINE = {
    "bitcoin", "ethereum", "tether", "bnb", "xrp", "usd-coin", "solana",
    "tron", "zcash", "hyperliquid", "dogecoin", "chainlink", "monero",
    "cardano", "stellar", "near-protocol", "litecoin", "avalanche",
    "shiba-inu", "aave", "uniswap", "pepe", "polkadot-new", "sui",
    "internet-computer", "ondo-finance", "cronos", "arbitrum",
    "pax-gold", "tether-gold",
}

# Nav/menu icons the mirror's header, sidebar and footer actually render.
MENU_ICONS = [
    "MenuCmcIconV3.svg", "MenuCategoriesIconV3.svg", "MenuHistoryIconV3.svg",
    "MenuTrendingIconV3.svg", "MenuUpcomingIconV3.svg",
    "MenuRecentlyAddedIconV3.svg", "MenuGainersLosersIconV3.svg",
    "MenuMostVisitedV3.svg", "MenuCommunitySentiment.svg",
    "MenuConverterIconV2.svg", "MenuMarketOverviewIcon.svg",
    "MenuSpotMarketIcon.svg", "MenuFearGreedIndexIcon.svg",
    "MenuAltcoinIndexIcon.svg", "MenuBitcoinDominanceV2.svg",
    "MenuCMC20Icon.svg", "MenuCMC100IconV2.svg", "MenuNFTOverviewV3.svg",
    "MenuGlossaryIconV2.svg", "MenuNewsIconV2.svg", "MenuVideosIconV2.svg",
    "MenuAlexandriaIconV2.svg", "MenuRewardsIconV2.svg",
    "MenuApiCryptoIcon.svg", "MenuWidgetsIconV2.svg", "MenuYieldIconV2.svg",
    "MenuRealWorldAssetsIcon.svg", "MenuExplorerIconV2.svg",
    "MenuDerivativesIcon.svg", "MenuEvents2IconV2.svg",
    "MenuEarnCryptoIconV2.svg", "MenuAirdropsIconV2.svg",
    "MenuBitcoinTreasuriesIcon.svg", "MenuExchangeInflowsOutflowsIcon.svg",
    "MenuNumberOfCryptocurrenciesIcon.svg", "MenuRSIV2.svg", "MenuMACD.svg",
    "MenuFundingRates.svg", "MenuLiquidationMapIcon.svg",
    "MenuChainRankingV4.svg", "MenuMktCycle.svg", "MenuLaunchIcon.svg",
    "MenuNewsletterIconV2.svg", "MenuTelegramBotIconV2.svg",
    "MenuAdvertiseIconV2.svg", "MenuCMCAIIcon.svg", "MenuCMCMax.svg",
    "MenuCMCResearchV2.svg", "MenuBitcoinETFsIconV4.svg",
    "MenuEthereumETFsIcon.svg", "MenuSolanaETFsIcon.svg",
    "MenuXrpETFsIcon.svg", "MenuTokenUnlocksIconV2.svg",
    "MenuHypeETFsIcon.svg", "MenuDerivativesMarketIcon.svg",
    "MenuDexSpotIcon.svg", "MenuDexDerivativesIcon.svg",
    "MenuDexScanNewPairs.svg", "MenuDexScanTrendingPairs.svg",
    "MenuDexScanGainersAndLosers.svg", "MenuDexScanMemeExplorer.svg",
    "MenuDexScanSignals.svg", "MenuDexScanTopTraders.svg",
    "MenuAgenticChartsIcon.svg", "MenuCMCAIAlertsIcon.svg",
    "MenuUpcomingSales.svg", "MenuICOIconV2.svg", "articles.svg",
    "feed.svg", "lives.svg", "topics.svg", "AITopStoriesIcon.svg",
    "LiquidationsIcon.svg", "PredictionMktCrypto.svg",
    "PredictionMktNews.svg", "PredictionMktSports.svg",
    "PredictionMktPolitics.svg", "PredictionMktFinance.svg",
    "PredictionMktTech.svg", "MenuApiDocumentationIcon.svg",
    "MenuApiPricingIcon.svg", "MenuApiMcpIcon.svg", "MenuApiWebsocketIcon.svg",
    "MenuApiEnterpriseIcon.svg", "MenuApiRwaIcon.svg", "MenuApiX402Icon.svg",
    "MenuApiKeylessIcon.svg", "MenuApiFaqIcon.svg", "MenuApiCaseStudiesIcon.svg",
    "MenuApiDexIcon.svg", "MenuApiResourcesIcon.svg",
]

inventory: list[dict] = []


def fetch(url: str, referer: str | None = None, retries: int = 5) -> bytes:
    last = None
    for attempt in range(retries):
        headers = {"User-Agent": UA}
        if referer:
            headers["Referer"] = referer
        try:
            r = requests.get(url, headers=headers, timeout=40)
            if r.status_code == 200 and len(r.content) > 100:
                return r.content
            last = f"HTTP {r.status_code} ({len(r.content)}B)"
        except requests.RequestException as e:
            last = str(e)
        time.sleep(2 + attempt * 3)
    raise RuntimeError(f"fetch failed: {url} ({last})")


def store(rel: str, url: str, referer: str | None = None) -> None:
    target = IMAGES / rel
    if target.exists():
        data = target.read_bytes()
    else:
        data = fetch(url, referer)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    inventory.append({
        "path": f"static/images/upstream/{rel}",
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "source_url": url,
    })


def main() -> None:
    corpus = json.loads((CAPTURES / "corpus.json").read_text())
    by_slug = {c["slug"]: c for c in corpus}

    print(f"[images] {len(corpus)} coins")
    for i, c in enumerate(corpus):
        cid = c["id"]
        store(f"coins/64x64/{cid}.png", f"{S2}/static/img/coins/64x64/{cid}.png")
        if c["slug"] in HEADLINE:
            store(f"coins/200x200/{cid}.png", f"{S2}/static/img/coins/200x200/{cid}.png")
        store(f"sparklines/7d/{cid}.svg",
              f"{S3}/generated/sparklines/web/7d/2781/{cid}.svg",
              referer="https://coinmarketcap.com/")
        if i % 20 == 19:
            print(f"  {i+1}/{len(corpus)} coins done")
            time.sleep(1)

    print("[images] exchanges")
    ex_slugs = sorted(p.name.removeprefix("exdetail_").removesuffix(".json")
                      for p in CAPTURES.glob("exdetail_*.json")
                      if p.name.endswith(".json") and not p.name.endswith(".meta.json"))
    for slug in ex_slugs:
        d = json.loads((CAPTURES / f"exdetail_{slug}.json").read_text())["data"]
        store(f"exchanges/64x64/{d['id']}.png",
              f"{S2}/static/img/exchanges/64x64/{d['id']}.png")

    print("[images] brand + menu icons")
    store("brand/coinmarketcap_1.svg", f"{S2}/static/cloud/img/coinmarketcap_1.svg")
    store("brand/favicon.ico", f"{SITE}/favicon.ico")
    store("brand/apple-touch-icon.png", f"{SITE}/apple-touch-icon.png")
    store("brand/splash_600x315_1.png", f"{S2}/static/cloud/img/splash_600x315_1.png")
    store("brand/default-coin-icon.svg", f"{S2}/static/cloud/img/dex/default-icon-day-v3.svg")
    for icon in MENU_ICONS:
        try:
            store(f"menu/{icon}", f"{S2}/static/cloud/img/menu/{icon}")
        except RuntimeError as e:
            print(f"  ! {icon}: {e}")

    inventory.sort(key=lambda r: r["path"])
    out = HERE / "asset_inventory.json"
    out.write_text(json.dumps(
        {"schema_version": 1, "asset_count": len(inventory),
         "assets": inventory}, indent=1) + "\n", encoding="utf-8")
    print(f"[images] {len(inventory)} assets inventoried -> {out}")


if __name__ == "__main__":
    main()
