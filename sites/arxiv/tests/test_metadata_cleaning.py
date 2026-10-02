"""Scientific metadata preservation and deterministic seed-migration regressions."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from types import SimpleNamespace

SITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE))
from metadata_cleaning import CORRECTIONS, clean_paper_metadata_fields
from migrate_seed import migrate


class MetadataTests(unittest.TestCase):
    def test_source_checked_fixtures(self):
        self.assertEqual(len(CORRECTIONS), 22)
        self.assertEqual(len({x['arxiv_id'] for x in CORRECTIONS}), 22)
        for correction in CORRECTIONS:
            with self.subTest(paper=correction['arxiv_id']):
                paper = {'arxiv_id': correction['arxiv_id'],
                         'title': correction['captured']}
                self.assertEqual(clean_paper_metadata_fields(paper),
                                 {'title': correction['corrected']})
                self.assertEqual(clean_paper_metadata_fields(SimpleNamespace(**paper)),
                                 {'title': correction['corrected']})
                paper['title'] = correction['corrected']
                self.assertEqual(clean_paper_metadata_fields(paper), {})
                self.assertEqual(correction['source_url'],
                                 'https://arxiv.org/abs/' + correction['arxiv_id'])
                self.assertTrue(correction['source_title_tex'])

    def test_exact_paper_and_exact_value_required(self):
        for correction in CORRECTIONS:
            self.assertEqual(clean_paper_metadata_fields({
                'arxiv_id': 'unknown', 'title': correction['captured']}), {})
            self.assertEqual(clean_paper_metadata_fields({
                'arxiv_id': correction['arxiv_id'],
                'title': 'Updated: ' + correction['captured']}), {})

    def test_valid_repeated_math_is_untouched(self):
        expressions = [r'(x+1)(x+1)', r'$\alpha\alpha$', r'\log\log n',
                       r'\log\log\log n', r'K_{11,11}', r'^{\prime\prime}',
                       r'$x$$x$', r'(AB)(AB)', r'\log \log n', None, '']
        for identifier in ['unknown', CORRECTIONS[0]['arxiv_id']]:
            for expression in expressions:
                for field in ['title', 'abstract', 'comments', 'journal_ref']:
                    self.assertEqual(clean_paper_metadata_fields({
                        'arxiv_id': identifier, field: expression}), {})

    def test_only_title_changes_even_for_known_paper(self):
        c = CORRECTIONS[0]
        paper = {'arxiv_id': c['arxiv_id'], 'title': c['captured'],
                 'abstract': r'O(n\log\log n)', 'comments': '(x+1)(x+1)',
                 'journal_ref': r'$\alpha\alpha$'}
        self.assertEqual(clean_paper_metadata_fields(paper), {'title': c['corrected']})

    def test_verified_numerical_and_display_fixes(self):
        titles = {c['arxiv_id']: c['corrected'] for c in CORRECTIONS}
        self.assertEqual(titles['2506.02455'], 'Perfect 1-factorisations of K₁₁,₁₁')
        self.assertIn('𝒩=2 to 4 SCFT₃', titles['2604.07503'])
        self.assertIn('≳ 100×', titles['2604.07983'])
        for title in titles.values():
            self.assertNotIn('$', title)
            self.assertNotIn('\\', title)

    def test_tracked_corpus_repairs_are_idempotent(self):
        papers = json.loads((SITE / 'papers.json').read_text())
        changed = 0
        for paper in papers:
            updates = clean_paper_metadata_fields(paper)
            changed += bool(updates)
            self.assertFalse(clean_paper_metadata_fields(paper | updates))
        self.assertEqual(changed, 22)


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'seed.db'
        with sqlite3.connect(self.path) as db:
            db.executescript('CREATE TABLE papers (arxiv_id TEXT PRIMARY KEY, title TEXT, abstract TEXT);'
                             'CREATE TABLE users (id INTEGER, name TEXT);'
                             "INSERT INTO users VALUES (1, 'keep me');")
            db.executemany('INSERT INTO papers VALUES (?,?,?)',
                           [(c['arxiv_id'], c['captured'], r'O(n\log\log n)')
                            for c in CORRECTIONS])
            db.execute('INSERT INTO papers VALUES (?,?,?)',
                       ('unknown', '(x+1)(x+1)', r'\log\log\log n'))

    def digest(self):
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def test_check_mode_does_not_write(self):
        before = self.digest()
        self.assertEqual(migrate(self.path, check=True), 22)
        self.assertEqual(before, self.digest())

    def test_updates_only_known_titles_and_preserves_user_data(self):
        self.assertEqual(migrate(self.path), 22)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT * FROM users').fetchall(), [(1, 'keep me')])
            self.assertEqual(db.execute("SELECT title FROM papers WHERE arxiv_id='unknown'").fetchone(),
                             ('(x+1)(x+1)',))
            for c in CORRECTIONS:
                self.assertEqual(db.execute('SELECT title,abstract FROM papers WHERE arxiv_id=?',
                                            (c['arxiv_id'],)).fetchone(),
                                 (c['corrected'], r'O(n\log\log n)'))

    def test_repeated_migration_is_byte_identical(self):
        migrate(self.path)
        before = self.digest()
        self.assertEqual(migrate(self.path), 0)
        self.assertEqual(migrate(self.path, check=True), 0)
        self.assertEqual(before, self.digest())

    def test_two_identical_inputs_produce_identical_outputs(self):
        other = self.path.with_name('other.db')
        other.write_bytes(self.path.read_bytes())
        migrate(self.path)
        migrate(other)
        self.assertEqual(self.path.read_bytes(), other.read_bytes())

    def test_missing_database_is_not_created(self):
        missing = self.path.with_name('missing.db')
        with self.assertRaises(sqlite3.OperationalError):
            migrate(missing)
        self.assertFalse(missing.exists())

    def test_edited_known_title_is_preserved(self):
        with sqlite3.connect(self.path) as db:
            db.execute('UPDATE papers SET title=? WHERE arxiv_id=?',
                       ('Author revision (x+1)(x+1)', CORRECTIONS[0]['arxiv_id']))
        self.assertEqual(migrate(self.path), 21)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT title FROM papers WHERE arxiv_id=?',
                                        (CORRECTIONS[0]['arxiv_id'],)).fetchone()[0],
                             'Author revision (x+1)(x+1)')


if __name__ == '__main__':
    unittest.main()
