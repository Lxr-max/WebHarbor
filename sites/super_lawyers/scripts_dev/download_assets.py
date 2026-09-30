"""Download every real upstream image referenced by the harvested
source_data into static/images/ and build asset_inventory.json.

Sources: lawyer photos (card + full variants), firm static maps, hero and
legal-issue card art, nav icons, the Super Lawyers logo, and the favicon.
Every file keeps its real CDN/Google source URL, byte size, and SHA-256 in
asset_inventory.json (the check_asset_inventory.py gate verifies this).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

import httpx

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
SRC = SITE / "source_data"
IMG = SITE / "static" / "images"

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/131.0.0.0 Safari/537.36"),
      "Referer": "https://www.superlawyers.com/"}

# fixed site art captured from the homepage render
SITE_ART = {
    "hero_home_lg.jpg": "https://cdn.superlawyers.com/image/upload/q_auto,f_auto/v1678323363/resources/superlawyers/images/hero/hero-home-lg.jpg",
    "why_superlawyers.jpg": "https://cdn.superlawyers.com/image/upload/q_auto,f_auto,h_142,w_154/v1678323363/resources/superlawyers/images/image-why-sl.jpg",
    "card_motor_vehicle_accidents.jpg": "https://cdn.superlawyers.com/image/upload/h_130,w_408,q_auto,f_auto/v1678323363/resources/superlawyers/images/legal-issue-cards/motor-vehicle-accidents.jpg",
    "card_family_law.jpg": "https://cdn.superlawyers.com/image/upload/h_130,w_408,q_auto,f_auto/v1678323363/resources/superlawyers/images/legal-issue-cards/family-law.jpg",
    "card_criminal_defense.jpg": "https://cdn.superlawyers.com/image/upload/h_130,w_408,q_auto,f_auto/v1678323363/resources/superlawyers/images/legal-issue-cards/criminal-defense.jpg",
    "card_employment_and_labor.jpg": "https://cdn.superlawyers.com/image/upload/h_130,w_408,q_auto,f_auto/v1678323363/resources/superlawyers/images/legal-issue-cards/employment-and-labor.jpg",
    "card_estate_planning_and_probate.jpg": "https://cdn.superlawyers.com/image/upload/h_130,w_408,q_auto,f_auto/v1678323363/resources/superlawyers/images/legal-issue-cards/estate-planning-and-probate.jpg",
    "card_key_legal_needs.jpg": "https://cdn.superlawyers.com/image/upload/h_130,w_408,q_auto,f_auto/v1678323363/resources/superlawyers/images/legal-issue-cards/key-legal-needs.jpg",
    "icon_legal_issue_family_law.png": "https://cdn.superlawyers.com/image/upload/c_pad,h_55,w_55,q_auto,f_auto/v1658902901/resources/superlawyers/images/icons/legal-issue/family-law.png",
    "icon_legal_issue_personal_injury.png": "https://cdn.superlawyers.com/image/upload/c_pad,h_55,w_55,q_auto,f_auto/v1658902901/resources/superlawyers/images/icons/legal-issue/personal-injury-plaintiff.png",
    "icon_legal_issue_criminal_defense.png": "https://cdn.superlawyers.com/image/upload/c_pad,h_55,w_55,q_auto,f_auto/v1658902901/resources/superlawyers/images/icons/legal-issue/criminal-defense.png",
    "icon_legal_issue_estate_planning.png": "https://cdn.superlawyers.com/image/upload/c_pad,h_55,w_55,q_auto,f_auto/v1658902901/resources/superlawyers/images/icons/legal-issue/estate-planning-and-probate.png",
    "icon_legal_issue_employment.png": "https://cdn.superlawyers.com/image/upload/c_pad,h_55,w_55,q_auto,f_auto/v1658902901/resources/superlawyers/images/icons/legal-issue/employment-and-labor.png",
    "icon_legal_issue_business.png": "https://cdn.superlawyers.com/image/upload/c_pad,h_55,w_55,q_auto,f_auto/v1658902901/resources/superlawyers/images/icons/legal-issue/business-and-corporate.png",
    "icon_legal_issue_elder_law.png": "https://cdn.superlawyers.com/image/upload/c_pad,h_55,w_55,q_auto,f_auto/v1658902901/resources/superlawyers/images/icons/legal-issue/elder-law.png",
    "icon_legal_issue_real_estate.png": "https://cdn.superlawyers.com/image/upload/c_pad,h_55,w_55,q_auto,f_auto/v1658902901/resources/superlawyers/images/icons/legal-issue/real-estate.png",
    "icon_article.png": "https://cdn.superlawyers.com/image/upload/h_38,w_38,c_pad,g_east,q_auto,f_auto/v1678323363/resources/superlawyers/images/icons/icon-article.png",
    "icon_search_ask.png": "https://cdn.superlawyers.com/image/upload/h_38,w_38,c_pad,g_east,q_auto,f_auto/v1678323363/resources/superlawyers/images/icons/icon-search-ask.png",
    "icon_resources.png": "https://cdn.superlawyers.com/image/upload/h_38,w_38,c_pad,g_east,q_auto,f_auto/v1678323363/resources/superlawyers/images/icons/icon-resources.png",
    "icon_search_person.png": "https://cdn.superlawyers.com/image/upload/h_38,w_38,c_pad,g_east,q_auto,f_auto/v1678323363/resources/superlawyers/images/icons/icon-search-person.png",
    "icon_magazine.png": "https://cdn.superlawyers.com/image/upload/h_38,w_38,c_pad,g_east,q_auto,f_auto/v1678323363/resources/superlawyers/images/icons/icon-magazine.png",
    "icon_question.png": "https://cdn.superlawyers.com/image/upload/h_38,w_38,c_pad,g_east,q_auto,f_auto/v1678323363/resources/superlawyers/images/icons/icon-question.png",
    "icon_lightbulb.png": "https://cdn.superlawyers.com/image/upload/h_38,w_38,c_pad,g_east,q_auto,f_auto/v1678323363/resources/superlawyers/images/icons/icon-lightbulb.png",
    "icon_law_practice_resources.png": "https://cdn.superlawyers.com/image/upload/c_pad,h_55,w_70,q_auto,f_auto/v1658960042/resources/superlawyers/images/icons/icon-law-practice-resources.png",
    "icon_marketing_opportunities.png": "https://cdn.superlawyers.com/image/upload/c_pad,h_55,w_70,q_auto,f_auto/v1658960042/resources/superlawyers/images/icons/icon-marketing-opportunities.png",
    "icon_get_involved.png": "https://cdn.superlawyers.com/image/upload/c_pad,h_55,w_70,q_auto,f_auto/v1658960042/resources/superlawyers/images/icons/icon-get-involved-with-sl.png",
    "logo.svg": "https://cdn.superlawyers.com/image/upload/fl_sanitize/v1678323363/resources/shared/superlawyers-logo-ib_theme.svg",
    # the circled-headshot icon upstream serves in the photo slot of any
    # lawyer without a real headshot (photo-less profiles, list cards,
    # featured-lawyer cards)
    "icon_headshot_circled.png": "https://cdn.superlawyers.com/image/upload/c_pad,w_165,ar_1/q_auto,f_auto,c_lpad,w_200,ar_4:5,b_rgb:FFF,r_9,bo_2px_solid_rgb:949494/v1678323363/resources/superlawyers/images/icons/icon-headshot-circled.png",
}

# selection icons used on profile sidebars
SELECTION_ART = {
    "icon_sl_selection.svg": "https://cdn.superlawyers.com/image/upload/c_pad,f_auto,q_auto/v1678323363/resources/superlawyers/images/icons/icon-sl-selection.svg",
    "icon_rs_selection.svg": "https://cdn.superlawyers.com/image/upload/c_pad,h_24,w_24,c_pad,h_24,w_24,f_auto,q_auto/v1678323363/resources/superlawyers/images/icons/icon-rs-selection.svg",
}


def ext_for(content_type: str, url: str, data: bytes) -> str:
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct == "image/jpeg" or (data[:2] == b"\xff\xd8"):
        return ".jpg"
    if ct == "image/png" or data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if ct == "image/webp" or (data[:4] == b"RIFF" and data[8:12] == b"WEBP"):
        return ".webp"
    if ct == "image/svg+xml" or b"<svg" in data[:512]:
        return ".svg"
    if ct == "image/x-icon" or data[:4] == b"\x00\x00\x01\x00":
        return ".ico"
    if ct == "image/gif":
        return ".gif"
    raise ValueError(f"unknown image type {ct!r} for {url[:80]}")


def main() -> None:
    inventory = []

    def save(rel: str, url: str, data: bytes):
        path = IMG / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        inventory.append({
            "path": f"static/images/{rel}", "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "source_url": url,
        })

    client = httpx.Client(follow_redirects=True, timeout=60, headers=UA)
    maps_client = None  # created lazily via Playwright for signed maps

    def get(url: str, referer=None):
        headers = dict(UA)
        if referer:
            headers["Referer"] = referer
        r = httpx.Client(follow_redirects=True, timeout=60,
                         headers=headers).get(url)
        r.raise_for_status()
        return r

    # ---- fixed site art ---------------------------------------------------
    for rel, url in {**SITE_ART, **SELECTION_ART}.items():
        if any(a["path"] == f"static/images/{rel}" for a in inventory):
            continue
        try:
            data = get(url).content
        except Exception as exc:  # noqa: BLE001
            print(f"[art-skip] {rel}: {exc}")
            continue
        # f_auto may serve a different format than the extension suggests;
        # keep the inventory honest by re-exting from the actual bytes.
        real_ext = ext_for(None, url, data)
        stem = rel.rsplit(".", 1)[0]
        save(f"{stem}{real_ext}", url, data)
    print(f"[art] {len(inventory)} fixed assets")

    # ---- lawyer photos ----------------------------------------------------
    lawyers_done = set()
    for path in sorted((SRC / "lawyers").glob("*.json")):
        rec = json.loads(path.read_text())
        uuid = path.stem
        if uuid in lawyers_done or not rec.get("photo_url"):
            continue
        lawyers_done.add(uuid)
        url = rec["photo_url"]
        data = get(url, referer="https://profiles.superlawyers.com/").content
        ext = ext_for(None, url, data)
        save(f"lawyers/{uuid}{ext}", url, data)
    # card variants from the listings (cropped 4:5)
    card_done = set()
    for path in sorted((SRC / "listings").glob("*.json")):
        data_rec = json.loads(path.read_text())
        for card in data_rec["cards"]:
            uuid = card.get("profile_uuid")
            if not uuid or uuid in card_done or not card.get("photo_url"):
                continue
            card_done.add(uuid)
            url = card["photo_url"]
            data = get(url, referer="https://attorneys.superlawyers.com/").content
            ext = ext_for(None, url, data)
            save(f"lawyers/{uuid}_card{ext}", url, data)
    print(f"[lawyers] photos: {len(lawyers_done)} full + {len(card_done)} cards")

    # ---- top-list photos ----------------------------------------------------
    tl = SRC / "toplists.json"
    tl_done = set()
    if tl.exists():
        toplists = json.loads(tl.read_text())
        for state, entry in toplists.get("states", {}).items():
            for lst in entry.get("lists", []):
                for lw in lst.get("lawyers", []):
                    uuid = lw.get("uuid")
                    if not uuid or uuid in tl_done or not lw.get("photo_url"):
                        continue
                    tl_done.add(uuid)
                    url = lw["photo_url"]
                    data = get(url, referer="https://www.superlawyers.com/").content
                    ext = ext_for(None, url, data)
                    save(f"lawyers/{uuid}_top{ext}", url, data)
    print(f"[toplists] {len(tl_done)} photos")

    # ---- Ask-a-Lawyer answerer photos ---------------------------------------
    ans_done = set()
    for path in sorted((SRC / "answers").glob("*.json")):
        rec = json.loads(path.read_text())
        ans = rec.get("answerer") or {}
        photo = ans.get("photo_url")
        puuid = ans.get("profile_uuid")
        if not photo or not puuid or puuid in ans_done:
            continue
        ans_done.add(puuid)
        data = get(photo, referer="https://answers.superlawyers.com/").content
        ext = ext_for(None, photo, data)
        save(f"answers/{puuid}{ext}", photo, data)
    print(f"[answers] {len(ans_done)} answerer photos")

    # ---- firm static maps ----------------------------------------------------
    maps_pw = None
    firm_done = set()
    for path in sorted((SRC / "firms").glob("*.json")):
        rec = json.loads(path.read_text())
        uuid = path.stem
        url = rec.get("static_map_url")
        if not url or uuid in firm_done:
            continue
        firm_done.add(uuid)
        try:
            data = get(url, referer="https://profiles.superlawyers.com/").content
        except Exception:
            # signed Google maps need the browser stack
            if maps_pw is None:
                from sl_browser import launch
                maps_pw, maps_browser, maps_ctx = launch()
            r = maps_ctx.request.get(url, headers={
                "Referer": "https://profiles.superlawyers.com/"})
            if r.status != 200:
                print(f"[map-fail] {uuid}: {r.status}")
                continue
            data = r.body()
        save(f"maps/{uuid}.png", url, data)
    print(f"[maps] {len(firm_done)} firm maps")
    if maps_pw:
        maps_browser.close()
        maps_pw.stop()

    client.close()

    # also lawyer-profile static maps (office location tab)
    # (already covered: the firm map is the same image upstream shows)

    # favicon via the browser stack (www host 403s plain httpx)
    from sl_browser import launch  # noqa: PLC0415
    pw_f, browser_f, ctx_f = launch()
    r = ctx_f.request.get("https://www.superlawyers.com/favicon.ico",
                          headers={"Referer": "https://www.superlawyers.com/"})
    if r.status == 200:
        save("favicon.ico", "https://www.superlawyers.com/favicon.ico", r.body())
    else:
        print(f"[favicon] status {r.status}")
    browser_f.close()
    pw_f.stop()

    manifest = SITE / "asset_inventory.json"
    manifest.write_text(json.dumps({
        "schema_version": 1,
        "asset_count": len(inventory),
        "assets": sorted(inventory, key=lambda a: a["path"]),
    }, indent=1, ensure_ascii=False) + "\n")
    print(f"[inventory] {len(inventory)} assets -> {manifest}")


if __name__ == "__main__":
    main()
