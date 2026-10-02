"""Fallback behavior must preserve team/league identity and avoid broken URLs."""
import sys
import tempfile
import unittest
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE))
from app import app, espn_asset_url, league_icon_url, static_exists, team_icon_url, team_logo_url


class IconTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.static = Path(self.tmp.name)
        original_static = app.static_folder
        app.static_folder = str(self.static)
        self.addCleanup(setattr, app, 'static_folder', original_static)
        self.context = app.test_request_context('/')
        self.context.push()
        self.addCleanup(self.context.pop)
        self.put('icons/sport-placeholder.svg')

    def put(self, path):
        target = self.static / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'fixture')

    def test_present_named_assets_take_precedence(self):
        self.put('images/espn/leagues/ncaaf.png')
        self.assertTrue(league_icon_url('NCAAF').endswith('/images/espn/leagues/ncaaf.png'))
        self.put('images/espn/teams/soccer/psg.png')
        self.assertEqual(team_icon_url('soccer', 'PSG'), team_logo_url('soccer', 'psg'))
        self.assertTrue(team_logo_url('soccer', 'PSG').endswith('/teams/soccer/psg.png'))

    def test_missing_college_art_never_uses_professional_league_brand(self):
        self.put('images/espn/leagues/nfl.png')
        self.put('images/espn/leagues/nba.png')
        for slug in ['ncaaf', 'ncaam', 'ncaaw', 'college-football', 'mens-college-basketball']:
            with self.subTest(slug=slug):
                self.assertTrue(league_icon_url(slug).endswith('/icons/sport-placeholder.svg'))

    def test_route_aliases_only_use_same_sport(self):
        for route, slug in [('college-football', 'ncaaf'), ('mens-college-basketball', 'ncaam'), ('womens-college-basketball', 'ncaaw')]:
            self.put(f'images/espn/leagues/{slug}.png')
            self.assertEqual(league_icon_url(route), league_icon_url(slug))

    def test_missing_team_does_not_borrow_a_league_or_another_team(self):
        self.put('images/espn/leagues/nba.png')
        self.put('images/espn/teams/nba/bos.png')
        self.assertEqual(team_logo_url('nba', 'missing'), '')
        self.assertTrue(team_icon_url('nba', 'missing').endswith('/icons/sport-placeholder.svg'))

    def test_unsafe_paths_and_slugs_are_rejected(self):
        for path in ['/etc/passwd', '../app.py', 'images/../app.py', 'images\\x', '', './icons/sport-placeholder.svg']:
            self.assertFalse(static_exists(path))
            self.assertEqual(espn_asset_url(path), '')
        for slug in ['../nba', 'soccer/psg', '', None, '<script>']:
            self.assertEqual(team_logo_url(slug, 'psg'), '')
            self.assertTrue(league_icon_url(slug).endswith('/icons/sport-placeholder.svg'))

    def test_missing_optional_assets_return_empty_and_directories_are_not_files(self):
        (self.static / 'directory').mkdir()
        self.assertEqual(espn_asset_url('missing.png'), '')
        self.assertFalse(static_exists('directory'))
        self.assertTrue(espn_asset_url('missing.png', 'icons/sport-placeholder.svg').endswith('/icons/sport-placeholder.svg'))

    def test_newly_installed_asset_is_picked_up_without_process_restart(self):
        self.assertTrue(league_icon_url('soccer').endswith('/icons/sport-placeholder.svg'))
        self.put('images/espn/leagues/soccer.png')
        self.assertTrue(league_icon_url('soccer').endswith('/leagues/soccer.png'))


if __name__ == '__main__':
    unittest.main()
