"""Regression tests for the r1 NEEDS-FIX items (fix branch).

Covers: manual/quiz images served from real upstream captures, receipt
money formatting, online-services link mapping (no dead links), news/finder
count tightening, the upstream-data homepage, the fee-chart edition date in
GUI, office-link existence gating, and the dl1p application link resolution.
"""
from __future__ import annotations

import hashlib
import json
import re

from conftest import with_csrf


# ----------------------------------------------------- manual/quiz images --
def test_manual_subsection_images_served_locally(client):
    r = client.get("/drivers-manual/2/1")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "dmv-manuals/manuals/images" not in html, \
        "upstream image URLs must be rewritten to mirrored files"
    refs = re.findall(r'src="(/static/images/manual/[^"]+)"', html)
    assert refs, "manual subsection must reference its figures"
    for ref in refs:
        asset = client.get(ref)
        assert asset.status_code == 200, f"manual image {ref} missing"
        assert asset.data[:2] in (b"\xff\xd8", b"\x89P")


def test_every_manual_image_asset_exists_and_is_unique():
    import os
    import pathlib
    base = pathlib.Path(__file__).resolve().parents[1]
    manual = base / "static" / "images" / "manual"
    files = sorted(p for p in manual.iterdir() if p.is_file())
    assert len(files) == 121
    seen = set()
    for f in files:
        data = f.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        assert digest not in seen, f"duplicate manual asset bytes: {f.name}"
        seen.add(digest)
        assert len(data) > 0
        assert data[:2] in (b"\xff\xd8", b"\x89P"), f"{f.name} not a JPEG/PNG"


def test_sign_questions_render_images(client):
    """The exam bank's picture questions (incl. the 38 road-sign questions)
    must render their mirrored illustrations on the exam and result pages."""
    base = client.application.config
    r = client.get("/licenses-ids/exams/practice-exam/2")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    imgs = re.findall(r'src="(/static/images/manual/[^"]+)"', html)
    assert len(imgs) >= 5, "section 2's image questions must show their figures"
    for ref in imgs:
        assert client.get(ref).status_code == 200


def test_quiz_images_map_covers_all_picture_questions():
    import pathlib
    base = pathlib.Path(__file__).resolve().parents[1]
    mapping = json.loads((base / "source_data" / "quiz_images.json").read_text())
    names = json.loads((base / "source_data" / "manual_image_map.json").read_text())
    manual = base / "static" / "images" / "manual"
    assert len(mapping) >= 70, "the upstream picture questions must be covered"
    for qid, files in mapping.items():
        for name in files:
            assert name in names
            assert (manual / name).is_file(), f"missing image {name} for {qid}"


# ----------------------------------------------------- receipt formatting --
def test_registration_receipt_amounts_formatted(alice):
    vid = 1  # alice's Camry
    data = with_csrf(alice, f"/account/vehicles/{vid}/renew",
                     {"years": "2"})
    r = alice.post(f"/account/vehicles/{vid}/renew", data=data)
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "$61.50" in html and "-$2.00" in html and "-$3.00" in html
    assert "61.5<" not in html and "2.0<" not in html, \
        "receipt line amounts must be money-formatted, not raw floats"


def test_license_receipt_amounts_formatted(alice):
    data = with_csrf(alice, "/account/license/renew", {"years": "8"})
    r = alice.post("/account/license/renew", data=data)
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "$32.00" in html
    assert "32.0<" not in html, \
        "receipt line amounts must be money-formatted, not raw floats"


# ----------------------------------------------------- link mapping fixes --
def test_online_services_catalog_has_no_dead_internal_links(client):
    r = client.get("/online-services-all")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    # uncaptured internal transaction URLs must NOT render as raw hrefs
    for dead in ("/online-services/replace-license", "/online-services/renew-license",
                 "/businesses/hauling", "/online-services/emergency-contact"):
        assert f'href="{dead}"' not in html, f"dead link rendered: {dead}"
    # they must still be present as plain text labels
    assert "Driver&#39;s License/CDL Replacement" in html
    # mapped services link to real routes
    assert 'href="/appointments"' in html
    assert 'href="/online-services/address-change"' in html


def test_office_link_existence_gate(client):
    """Upstream office links that have no mirrored office render as text."""
    r = client.get("/records")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'href="/locations/dmv-connects"' not in html
    # real offices still link
    r = client.get("/all-locations?q=Alexandria")
    assert 'href="/locations/alexandria"' in r.get_data(as_text=True)


def test_dl1p_application_link_resolves(client):
    r = client.get("/licenses-ids/license/replace")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'href="/download/forms/dl1p.pdf"' in html, \
        "the DL 1P application PDF is mirrored and must be linked"
    dl = client.get("/download/forms/dl1p.pdf")
    assert dl.status_code == 200 and dl.data[:4] == b"%PDF"


# ----------------------------------------------------- overlap tightening --
def test_news_list_does_not_print_the_total(client):
    r = client.get("/news")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "of 70 news items" not in html
    assert "Displaying 1 - 10" in html  # range still shown for orientation


def test_location_finder_pills_do_not_print_counts(client):
    r = client.get("/all-locations")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "DMV Select (58)" not in html
    assert "Customer Service Center (76)" not in html
    # but the filtered result count is still honest, action-derived data
    r = client.get("/all-locations?type=dmv_select")
    assert "58 locations found" in r.get_data(as_text=True)


# ----------------------------------------------------- homepage + fees GUI --
def test_home_renders_captured_upstream_home(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "What can we help you find today?" in html, "upstream hero missing"
    assert "Explore your online options" in html
    assert "Popular Services" in html
    assert "Ride in style with a personalized license plate" in html
    assert "Our Mission-Purpose" in html


def test_fee_chart_page_shows_form_number_and_edition(client):
    r = client.get("/vehicles/taxes-fees")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "Fee Chart (DMV 201, 08/10/2026, PDF)" in html, \
        "the DMV 201 edition date must be reachable in the GUI"
