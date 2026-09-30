"""Offline DOJ snapshot, browsing, and restart regression checks.

Run with the site's dependencies installed:
    python -m unittest discover -s tests -p 'test_us_doj.py' -v

Every database created by this suite lives in a temporary directory. The suite
does not alter the working site's instance or its published seed database.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from collections import Counter
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, quote, unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "sites" / "us_doj"
SOURCE_FILE = SITE / "source_data.json"
CA_UST = "/legal-careers/job/trial-attorney-bankruptcy-0"
CA_BOP = "/legal-careers/job/consolidated-legal-center-clc-attorney-43"
BAYER = "/opa/pr/antitrust-division-secures-seed-tying-and-loyalty-program-commitments-bayer"


class Markup(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    def links(self, prefix=""):
        return [attrs["href"] for tag, attrs in self.elements
                if tag == "a" and attrs.get("href", "").startswith(prefix)]


class SectionNavigation(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.active = None
        self.entries = []
        self.feed(html)

    def handle_starttag(self, tag, items):
        attrs = dict(items)
        if tag == "nav":
            if self.depth:
                self.depth += 1
            elif attrs.get("aria-label") == "Section navigation":
                self.depth = 1
        if self.depth and tag == "a":
            self.active = {"path": attrs.get("href"), "text": []}

    def handle_data(self, data):
        if self.active is not None:
            self.active["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.active is not None:
            self.entries.append({"path": self.active["path"], "label": " ".join("".join(self.active["text"]).split())})
            self.active = None
        if tag == "nav" and self.depth:
            self.depth -= 1


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
        cls.pages = cls.source["pages"]

    def test_snapshot_records_have_unique_paths_and_provenance(self):
        paths = [p["path"] for p in self.pages]
        self.assertEqual(len(paths), len(set(paths)))
        counts = Counter(p["kind"] for p in self.pages)
        self.assertGreaterEqual(counts["job"], 50)
        self.assertGreaterEqual(counts["news"], 50)
        for page in self.pages:
            with self.subTest(path=page["path"]):
                self.assertTrue(page["path"].startswith("/"))
                self.assertEqual(urlsplit(page["source_url"]).hostname, "www.justice.gov")
                self.assertTrue(page["title"] and page["body_html"] and page["body_text"])
                self.assertNotIn("[Truncated]", page["body_html"])
                self.assertNotIn("[Truncated]", page["body_text"])
                self.assertRegex(page["source_sha256"], r"^[0-9a-f]{64}$")
                datetime.fromisoformat(page["source_captured_at"].replace("Z", "+00:00"))
                if page["date"]:
                    date.fromisoformat(page["date"])
                if page["kind"] == "job":
                    self.assertTrue(page["organization"] and page["position"])
                    self.assertTrue(page["states"] and page["practice_areas"])

    def test_provenance_hashes_match_shipped_html(self):
        provenance = json.loads((SITE / "provenance.json").read_text(encoding="utf-8"))
        records = {p["path"]: p for p in provenance["pages"]}
        self.assertEqual(set(records), {p["path"] for p in self.pages})
        for page in self.pages:
            with self.subTest(path=page["path"]):
                record = records[page["path"]]
                self.assertEqual(record["original_html_sha256"], page["source_sha256"])
                self.assertEqual(record["local_html_sha256"], hashlib.sha256(page["body_html"].encode()).hexdigest())

    def test_downloaded_asset_bytes_match_source_manifest(self):
        provenance = json.loads((SITE / "provenance.json").read_text(encoding="utf-8"))
        self.assertTrue(provenance["assets"])
        for source_url, record in provenance["assets"].items():
            with self.subTest(url=source_url):
                asset = SITE / record["path"]
                self.assertTrue(asset.is_file())
                content = asset.read_bytes()
                self.assertEqual(len(content), record["bytes"])
                self.assertEqual(hashlib.sha256(content).hexdigest(), record["sha256"])
                if record["mime"] == "application/pdf":
                    self.assertTrue(content.startswith(b"%PDF-"))

    def test_imported_html_is_passive_and_all_local_references_resolve(self):
        routes = {p["path"] for p in self.pages} | {
            "/", "/search", "/news", "/news/press-releases", "/reference",
            "/legal-careers/vacancies",
        } | set(self.source.get("asset_routes", {}))
        forbidden = {"script", "iframe", "object", "embed", "form", "input", "button", "link", "style", "base"}
        for page in self.pages:
            with self.subTest(path=page["path"]):
                for tag, attrs in Markup(page["body_html"]).elements:
                    self.assertNotIn(tag, forbidden)
                    for name, value in attrs.items():
                        self.assertFalse(name.lower().startswith("on"), (tag, name))
                        self.assertNotIn(name, {"srcdoc", "srcset"})
                        if value:
                            self.assertIsNone(re.search(r"(?:javascript|vbscript)\s*:", value, re.I))
                        if name not in {"href", "src", "poster", "data"} or not value:
                            continue
                        self.assertFalse(urlsplit(value).scheme or value.startswith("//"), value)
                        target = urlsplit(value).path
                        if target.startswith("/static/"):
                            self.assertTrue((SITE / target.lstrip("/")).is_file(), target)
                        elif name == "href" and target:
                            self.assertIn(unquote(target), routes)
                if page["image_path"]:
                    self.assertTrue((SITE / page["image_path"].lstrip("/")).is_file())

    def test_reviewed_tasks_have_public_definitions_and_grading_metadata(self):
        tasks = [json.loads(line) for line in (SITE / "tasks.jsonl").read_text().splitlines() if line.strip()]
        self.assertGreaterEqual(len(tasks), 15)
        self.assertLessEqual(len(tasks), 20)
        self.assertEqual(len(tasks), len({task["id"] for task in tasks}))
        for task in tasks:
            self.assertEqual(set(task), {"web_name", "id", "ques", "web", "upstream_url", "verifier_path", "judge_rubric"})
            self.assertEqual(task["verifier_path"], "sites/us_doj/verify/verify.py")
            self.assertTrue(task["judge_rubric"].strip())
            self.assertEqual(task["web_name"], "U.S. DOJ")
            self.assertTrue(task["ques"].strip())
            self.assertEqual(urlsplit(task["upstream_url"]).hostname, "www.justice.gov")

    def test_native_accordions_retain_legacy_guidance_and_all_job_policies(self):
        records = {p["path"]: p for p in self.pages}
        legacy = records["/oip/submit-and-track-request-or-appeal"]["body_html"]
        self.assertIn('<details class="source-accordion"><summary>', legacy)
        self.assertIn("Submitted Prior to January 28, 2020", legacy)
        self.assertIn("FOIAonline", legacy)
        for path in (CA_UST, CA_BOP):
            job = records[path]["body_html"]
            self.assertEqual(job.count('<details class="source-accordion">'), 7)
            self.assertIn("<summary>Equal Employment Opportunity</summary>", job)
            self.assertIn("<summary>USAO Residency Requirement</summary>", job)


class BrowsingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(prefix="webharbor-doj-tests-")
        cls.instance = Path(cls.workspace.name) / "instance"
        cls.instance.mkdir()
        cls.old_seed_module = sys.modules.pop("seed_data", None)
        sys.path.insert(0, str(SITE))
        try:
            with patch.dict(os.environ, {"DOJ_INSTANCE_PATH": str(cls.instance)}):
                spec = importlib.util.spec_from_file_location("webharbor_test_us_doj_app", SITE / "app.py")
                cls.module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = cls.module
                spec.loader.exec_module(cls.module)
            cls.seed = sys.modules["seed_data"]
        finally:
            sys.path.remove(str(SITE))
            sys.modules.pop("seed_data", None)
            if cls.old_seed_module is not None:
                sys.modules["seed_data"] = cls.old_seed_module
        cls.module.app.config["TESTING"] = True
        cls.client = cls.module.app.test_client()
        cls.source = json.loads(SOURCE_FILE.read_text())
        cls.pages = cls.source["pages"]

    @classmethod
    def tearDownClass(cls):
        with cls.module.app.app_context():
            cls.module.db.session.remove()
            cls.module.db.engine.dispose()
        sys.modules.pop("webharbor_test_us_doj_app", None)
        cls.workspace.cleanup()

    def get(self, path, query=None, expected=200):
        response = self.client.get(path, query_string=query)
        self.assertEqual(response.status_code, expected, (path, query))
        return response

    def test_every_captured_detail_and_main_route_renders(self):
        for path in ["/", "/news", "/news/press-releases", "/search", "/legal-careers/vacancies"] + [p["path"] for p in self.pages]:
            with self.subTest(path=path):
                self.get(path)
        health = self.get("/_health").get_json()
        self.assertTrue(health["ok"])
        self.assertEqual(health["pages"], len(self.pages))
        self.get("/not-a-captured-page", expected=404)

    def test_database_preserves_all_snapshot_fields(self):
        module = self.module
        with module.app.app_context():
            stored = {record.path: record for record in module.db.session.scalars(module.db.select(module.Page)).all()}
            self.assertEqual(set(stored), {p["path"] for p in self.pages})
            for source in self.pages:
                with self.subTest(path=source["path"]):
                    for key, value in source.items():
                        self.assertEqual(getattr(stored[source["path"]], key), value, key)
            source_hash = module.db.session.get(module.SnapshotMeta, "source_file_sha256").value
            self.assertEqual(source_hash, sha256(SOURCE_FILE))
            aliases = module.db.session.get(module.SnapshotMeta, "asset_routes").value
            self.assertEqual(aliases, self.source["asset_routes"])

    def test_original_document_urls_serve_correct_local_bytes_and_mime(self):
        inventory = json.loads((SITE / "asset_inventory.json").read_text())
        records = {record["path"]: record for record in inventory["assets"]}
        self.assertTrue(self.source["asset_routes"])
        for path, alias in self.source["asset_routes"].items():
            with self.subTest(path=path):
                local_path = alias["path"]
                self.assertTrue(local_path.startswith("static/external_cache/"))
                self.assertIn(local_path, records)
                response = self.get(quote(path, safe="/"), {"inline": ""})
                try:
                    record = records[local_path]
                    self.assertEqual(alias["mime"], record["mime_type"])
                    self.assertEqual(hashlib.sha256(response.data).hexdigest(), record["sha256"])
                    self.assertEqual(len(response.data), record["bytes"])
                    self.assertEqual(response.mimetype, record["mime_type"])
                finally:
                    response.close()

    def test_source_section_navigation_renders_exact_labels_and_valid_targets(self):
        routes = {page["path"] for page in self.pages} | {"/", "/news", "/news/press-releases", "/legal-careers/vacancies"}
        checked = 0
        for page in self.pages:
            navigation = page.get("navigation", [])
            if not navigation:
                continue
            with self.subTest(path=page["path"]):
                for entry in navigation:
                    self.assertIn(entry["path"], routes)
                    self.assertTrue(entry["label"].strip())
                # Legal Careers has its own stable template sidebar. The new
                # source-backed sidebar handles the other component branches.
                if not page["path"].startswith("/legal-careers"):
                    rendered = SectionNavigation(self.get(page["path"]).text).entries
                    self.assertEqual(rendered, navigation)
                    checked += 1
        self.assertGreaterEqual(checked, 8)

    def test_california_filter_and_combined_job_facets(self):
        response = self.get("/legal-careers/vacancies", {"state": "ca"})
        self.assertEqual(set(Markup(response.text).links("/legal-careers/job/")), {CA_UST, CA_BOP})
        for query in [
            {"f[0]": "va_state:CA"},
            {"f[]": "va_state:CA"},
        ]:
            response = self.get("/legal-careers/vacancies", query)
            self.assertEqual(set(Markup(response.text).links("/legal-careers/job/")), {CA_UST, CA_BOP})
        response = self.get("/legal-careers/vacancies", {
            "state": "CA", "position": "Attorney", "practice_area": "Bankruptcy",
            "organization": "United States Trustee Program (USTP)",
        })
        self.assertEqual(Markup(response.text).links("/legal-careers/job/"), [CA_UST])
        response = self.get("/legal-careers/vacancies", {"state": "CA", "organization": "Criminal Division (CRM)"})
        self.assertIn("No vacancies found", response.text)

    def test_job_pagination_has_no_missing_or_duplicate_records(self):
        expected = {p["path"] for p in self.pages if p["kind"] == "job"}
        seen = []
        for index in range((len(expected) + 24) // 25):
            response = self.get("/legal-careers/vacancies", {"page": index})
            seen.extend(Markup(response.text).links("/legal-careers/job/"))
        self.assertEqual(len(seen), len(expected))
        self.assertEqual(set(seen), expected)
        first = Markup(self.get("/legal-careers/vacancies", {"sort_by": "title"}).text).links("/legal-careers/job/")
        titles = {p["path"]: p["title"].casefold() for p in self.pages}
        self.assertEqual([titles[path] for path in first], sorted(titles[p] for p in expected)[:25])

    def test_pagination_preserves_job_filters_and_clamps_invalid_pages(self):
        response = self.get("/legal-careers/vacancies", {"position": "Attorney", "sort_by": "title"})
        next_links = [attrs["href"] for tag, attrs in Markup(response.text).elements if attrs.get("aria-label") == "Next page"]
        self.assertEqual(len(next_links), 1)
        self.assertEqual(parse_qs(urlsplit(next_links[0]).query), {"position": ["Attorney"], "sort_by": ["title"], "page": ["1"]})
        first = Markup(self.get("/legal-careers/vacancies").text).links("/legal-careers/job/")
        for value in ["not-a-number", "-10"]:
            self.assertEqual(Markup(self.get("/legal-careers/vacancies", {"page": value}).text).links("/legal-careers/job/"), first)
        last = Markup(self.get("/legal-careers/vacancies", {"page": "1"}).text).links("/legal-careers/job/")
        self.assertEqual(Markup(self.get("/legal-careers/vacancies", {"page": "99999"}).text).links("/legal-careers/job/"), last)

    def test_news_filters_find_bayer_at_inclusive_date_boundary(self):
        response = self.get("/news/press-releases", {
            "search_api_fulltext": "Bayer", "topic": "antitrust", "component": "Antitrust Division",
            "year": "2026", "start_date": "2026-05-20", "end_date": "2026-05-20",
        })
        self.assertEqual(Markup(response.text).links("/opa/pr/"), [BAYER])
        response = self.get("/news", {"topic": "FRAUD", "start_date": "2026-05-20", "end_date": "2026-05-20"})
        self.assertNotIn(BAYER, Markup(response.text).links("/opa/pr/"))
        self.assertIn("No news items found", response.text)

    def test_news_pagination_covers_snapshot_and_preserves_topic(self):
        expected = {p["path"] for p in self.pages if p["kind"] == "news"}
        seen = []
        for index in range((len(expected) + 11) // 12):
            seen.extend(Markup(self.get("/news", {"page": index}).text).links("/opa/pr/"))
        self.assertEqual(len(seen), len(expected))
        self.assertEqual(set(seen), expected)
        response = self.get("/news", {"topic": "ANTITRUST", "sort_by": "field_date"})
        next_links = [attrs["href"] for tag, attrs in Markup(response.text).elements if attrs.get("aria-label") == "Next page"]
        self.assertEqual(len(next_links), 1)
        self.assertEqual(parse_qs(urlsplit(next_links[0]).query), {"topic": ["ANTITRUST"], "sort_by": ["field_date"], "page": ["1"]})
        dates = {p["path"]: p["date"] for p in self.pages}
        result_dates = [dates[path] for path in Markup(response.text).links("/opa/pr/")]
        self.assertEqual(result_dates, sorted(result_dates, reverse=True))

    def test_malformed_reference_urls_return_client_errors(self):
        for target in ("https://[broken", "http:///missing-host", "https://"):
            self.get("/reference", {"url": target}, expected=400)

    def test_invalid_dates_and_unsafe_reference_urls_are_rejected(self):
        for query in [{"start_date": "2026-02-30"}, {"end_date": "nonsense"}, {"start_date": "2026-09-20", "end_date": "2026-09-01"}]:
            self.get("/news", query, expected=400)
        for value in ["javascript:alert(1)", "data:text/html,test", "//example.com", ""]:
            self.get("/reference", {"url": value}, expected=400)
        response = self.get("/reference", {"url": "https://example.org/document", "label": "<script>alert(1)</script>"})
        self.assertNotIn("<script>alert(1)</script>", response.text)
        self.assertIn("&lt;script&gt;", response.text)
        self.assertIn("form-action 'self'", response.headers["Content-Security-Policy"])
        self.assertIn("frame-src 'none'", response.headers["Content-Security-Policy"])

    def test_runtime_reads_database_without_reopening_source_json(self):
        original = Path.read_text

        def forbid_snapshot_read(path, *args, **kwargs):
            if path.resolve() == SOURCE_FILE.resolve():
                raise AssertionError("A browsing request tried to reread source JSON")
            return original(path, *args, **kwargs)

        with patch.object(Path, "read_text", forbid_snapshot_read):
            for path in ["/", "/news", "/legal-careers/vacancies", CA_UST, "/search?query=Bayer"]:
                self.get(path)

    def test_seed_functions_and_fresh_boot_preserve_database_bytes(self):
        module = self.module
        database = self.instance / "us_doj.db"
        with module.app.app_context():
            module.db.session.remove()
            module.db.engine.dispose()
        before = sha256(database)
        with module.app.app_context():
            self.seed.seed_database(module.db, module.Page, module.SnapshotMeta)
            self.seed.seed_benchmark_users(module.db, module.User)
            self.assertEqual(module.db.session.scalar(module.db.select(module.db.func.count(module.User.id))), 4)
            module.db.session.remove()
            module.db.engine.dispose()
        self.assertEqual(sha256(database), before)
        restored = Path(self.workspace.name) / "restored"
        restored.mkdir(exist_ok=True)
        shutil.copy2(database, restored / "us_doj.db")
        script = "import app as site\nwith site.app.app_context():\n    assert site.db.session.scalar(site.db.select(site.db.func.count(site.Page.id))) > 0\n    site.db.session.remove()\n    site.db.engine.dispose()\n"
        subprocess.run([sys.executable, "-c", script], cwd=SITE,
                       env={**os.environ, "DOJ_INSTANCE_PATH": str(restored)},
                       check=True, capture_output=True, text=True, timeout=45)
        self.assertEqual(sha256(restored / "us_doj.db"), before)


if __name__ == "__main__":
    unittest.main()
