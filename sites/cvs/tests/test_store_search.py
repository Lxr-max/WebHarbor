"""Store-search and selection regressions using an isolated runtime database."""
from __future__ import annotations

from html.parser import HTMLParser
import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from flask import template_rendered


SITE = Path(__file__).resolve().parents[1]


class FormFields(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.forms = []
        self.form = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.form = {"action": attrs.get("action"), "fields": {}}
            self.forms.append(self.form)
        elif tag == "input" and self.form is not None and attrs.get("name"):
            self.form["fields"][attrs["name"]] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self.form = None


class StoreSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cvs-store-search-")
        cls.old_environment = os.environ.get("CVS_INSTANCE_PATH")
        cls.old_modules = {key: sys.modules.pop(key, None) for key in ("app", "seed_data")}
        sys.path.insert(0, str(SITE))
        os.environ["CVS_INSTANCE_PATH"] = cls.temp.name
        cls.site = importlib.import_module("app")
        cls.app = cls.site.app
        cls.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
        cls.database_before = cls.site.DB_PATH.read_bytes()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            cls.site.db.session.remove()
            cls.site.db.engine.dispose()
        for key, previous in cls.old_modules.items():
            sys.modules.pop(key, None)
            if previous is not None:
                sys.modules[key] = previous
        sys.path.remove(str(SITE))
        if cls.old_environment is None:
            os.environ.pop("CVS_INSTANCE_PATH", None)
        else:
            os.environ["CVS_INSTANCE_PATH"] = cls.old_environment
        cls.temp.cleanup()

    def setUp(self):
        self.client = self.app.test_client()

    def tearDown(self):
        self.assertEqual(self.site.DB_PATH.read_bytes(), self.database_before)

    def search(self, query):
        contexts = []

        def record(sender, template, context, **extra):
            contexts.append(context)

        template_rendered.connect(record, self.app)
        try:
            response = self.client.get("/store-locator/landing", query_string=query)
        finally:
            template_rendered.disconnect(record, self.app)
        self.assertEqual(response.status_code, 200)
        return response, contexts[-1]

    def test_city_state_and_formatted_full_address_find_captured_stores(self):
        _, baseline = self.search({"q": "Chicago"})
        expected = {store.id for store in baseline["stores"]}
        self.assertTrue(expected)
        for query in ("Chicago, IL", "  chicago ,   il  ", "IL Chicago"):
            with self.subTest(query=query):
                _, context = self.search({"q": query})
                self.assertEqual({store.id for store in context["stores"]}, expected)
        _, context = self.search({"q": "6315 SOUTH PULASKI RD, SUITE 1, CHICAGO, IL 60629"})
        self.assertEqual([store.id for store in context["stores"]], ["8502"])

    def test_search_keeps_partial_queries_and_service_intersections(self):
        _, baseline = self.search({"q": "Chicago", "service": ["Accepts WIC", "Drug disposal"]})
        expected = {store.id for store in baseline["stores"]}
        self.assertTrue(expected)
        _, context = self.search({"q": "Chicago, IL", "service": ["Accepts WIC", "Drug disposal"]})
        self.assertEqual({store.id for store in context["stores"]}, expected)
        _, context = self.search({"q": "Pulaski 60629"})
        self.assertEqual([store.id for store in context["stores"]], ["8502"])
        for query in ("!!!", "___", "%", "Nonexistent Place"):
            with self.subTest(query=query):
                _, context = self.search({"q": query})
                self.assertEqual(context["stores"], [])

    def test_selecting_store_preserves_city_and_repeated_service_filters(self):
        query = {"q": "Chicago", "service": ["Accepts WIC", "Drug disposal"]}
        response, before = self.search(query)
        form = next(form for form in FormFields(response.get_data(as_text=True)).forms
                    if form["action"] == "/store-locator/select/8502")
        selected = self.client.post(form["action"], data=form["fields"])
        self.assertEqual(selected.status_code, 302)
        destination = urlsplit(selected.location)
        self.assertEqual(destination.path, "/store-locator/landing")
        self.assertEqual(parse_qs(destination.query), {"q": ["Chicago"], "service": query["service"]})
        response = self.client.get(selected.location)
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn("Your selected store", text)
        self.assertIn(f'<h2>{before["total"]} store', text)
        with self.client.session_transaction() as session:
            self.assertEqual(session["selected_store"], "8502")


if __name__ == "__main__":
    unittest.main()
