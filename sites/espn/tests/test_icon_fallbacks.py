"""Homepage icon fallbacks for missing ESPN league and team PNGs (issue #3).

The published asset bundle does not ship every league/team mark the homepage
used to request. Templates must ask the resolvers for a file that exists.

Run with:

    python3 -m unittest discover -s sites/espn/tests -v
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
TEMPLATES = SITE / "templates"
PLACEHOLDER = SITE / "static" / "icons" / "sport-placeholder.svg"

# Paths from aiming-lab/WebHarbor#3 that 404 in the published bundle.
MISSING_LEAGUE_SLUGS = (
    "soccer",
    "ncaaf",
    "ncaam",
    "ncaaw",
    "tennis",
    "golf",
    "fantasy",
)
MISSING_TEAM_MARKS = (
    ("soccer", "psg"),
    ("soccer", "mia"),
    ("soccer", "rma"),
)
FORBIDDEN_SUFFIXES = tuple(
    f"images/espn/leagues/{slug}.png" for slug in MISSING_LEAGUE_SLUGS
) + tuple(
    f"images/espn/teams/{sport}/{abbr}.png" for sport, abbr in MISSING_TEAM_MARKS
)


def _template_text() -> str:
    chunks = []
    for path in sorted(TEMPLATES.glob("*.html")):
        chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


class IconTemplateContractTest(unittest.TestCase):
    def test_placeholder_svg_is_committed(self):
        data = PLACEHOLDER.read_bytes()
        self.assertTrue(data.startswith(b"<svg"), "placeholder is not an SVG")
        self.assertIn(b"#DD0000", data)

    def test_templates_do_not_hardcode_missing_pngs(self):
        text = _template_text()
        for suffix in FORBIDDEN_SUFFIXES:
            self.assertNotIn(suffix, text, suffix)
        self.assertIn("league_icon_url(", text)
        self.assertIn("team_icon_url(", text)
        self.assertIn("team_logo_url(", text)


class IconResolverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load by path so a sibling site's `app` module cannot shadow this one.
        spec = importlib.util.spec_from_file_location("espn_mirror_app", SITE / "app.py")
        espn = importlib.util.module_from_spec(spec)
        # Register before exec so Flask resolves static/ from this file, not cwd.
        sys.modules["espn_mirror_app"] = espn
        spec.loader.exec_module(espn)
        espn.app.config["TESTING"] = True
        cls.espn = espn
        cls.client = espn.app.test_client()

    def _static_ok(self, url: str) -> None:
        self.assertTrue(url.startswith("/static/"), url)
        for suffix in FORBIDDEN_SUFFIXES:
            self.assertNotIn(suffix, url)
        resp = self.client.get(url)
        try:
            self.assertEqual(resp.status_code, 200, url)
            self.assertGreater(len(resp.data), 20, url)
        finally:
            resp.close()

    def test_missing_league_slots_resolve_to_a_real_file(self):
        for slug in MISSING_LEAGUE_SLUGS:
            with self.subTest(slug=slug):
                with self.espn.app.test_request_context("/"):
                    url = self.espn.league_icon_url(slug)
                self._static_ok(url)

    def test_shipped_league_icons_are_preferred_when_present(self):
        for slug in ("nba", "nfl", "mlb", "nhl", "mma"):
            rel = f"images/espn/leagues/{slug}.png"
            if not self.espn.static_exists(rel):
                continue
            with self.subTest(slug=slug):
                with self.espn.app.test_request_context("/"):
                    url = self.espn.league_icon_url(slug)
                self.assertIn(rel, url)
                self._static_ok(url)

    def test_missing_soccer_clubs_do_not_reuse_pro_league_marks(self):
        for sport, abbr in MISSING_TEAM_MARKS:
            with self.subTest(team=f"{sport}/{abbr}"):
                with self.espn.app.test_request_context("/"):
                    logo = self.espn.team_logo_url(sport, abbr)
                    icon = self.espn.team_icon_url(sport, abbr)
                self.assertEqual(logo, "")
                self.assertNotIn("/leagues/nba.png", icon)
                self.assertNotIn("/leagues/nfl.png", icon)
                self._static_ok(icon)

    def test_unsafe_slugs_do_not_escape_static(self):
        with self.espn.app.test_request_context("/"):
            url = self.espn.league_icon_url("../secret")
            self.assertNotIn("..", url)
            self.assertFalse(self.espn.static_exists("../icons/sport-placeholder.svg"))
            self.assertFalse(self.espn.static_exists("/etc/passwd"))
            self.assertEqual(self.espn.team_logo_url("../soccer", "psg"), "")
        self._static_ok(url)


if __name__ == "__main__":
    unittest.main()
