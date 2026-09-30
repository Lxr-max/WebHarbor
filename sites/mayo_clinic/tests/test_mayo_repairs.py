import hashlib
import importlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SITE = Path(__file__).resolve().parents[1]
SEED = SITE / "instance_seed" / "mayo_clinic.db"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MayoRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.database = Path(cls.tempdir.name) / "mayo_clinic.db"
        shutil.copy2(SEED, cls.database)
        os.environ["MAYO_DATABASE_PATH"] = str(cls.database)
        sys.path.insert(0, str(SITE))
        cls.module = importlib.import_module("app")
        cls.app = cls.module.app
        cls.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            cls.module.db.session.remove()
        sys.path.remove(str(SITE))
        os.environ.pop("MAYO_DATABASE_PATH", None)
        cls.tempdir.cleanup()

    def setUp(self):
        with self.app.app_context():
            self.module.db.session.remove()
            self.module.db.engine.dispose()
        shutil.copy2(SEED, self.database)
        self.client = self.app.test_client()

    def test_catalog_identity_and_required_counts(self):
        with sqlite3.connect(self.database) as connection:
            expected = {
                "condition": 242,
                "doctor": 110,
                "clinical_trial": 40,
                "drug": 322,
            }
            for table, count in expected.items():
                self.assertEqual(
                    connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0],
                    count,
                )
            ids = [
                row[0]
                for row in connection.execute(
                    "SELECT nct_id FROM clinical_trial ORDER BY id"
                )
            ]
        self.assertEqual(ids[0], "SIM-MAYO-001")
        self.assertEqual(ids[-1], "SIM-MAYO-040")
        self.assertFalse(any(value.startswith("NCT") for value in ids))

    def test_tasks_have_basic_contract_and_feasible_targets(self):
        tasks = [
            json.loads(line)
            for line in (SITE / "tasks.jsonl").read_text().splitlines()
            if line.strip()
        ]
        self.assertEqual(len(tasks), 20)
        self.assertEqual(
            [task["id"] for task in tasks],
            [f"Mayo Clinic--{index}" for index in range(20)],
        )
        for task in tasks:
            self.assertEqual(
                set(task),
                {"web_name", "id", "ques", "web", "upstream_url", "verifier_path", "judge_rubric"},
            )
            self.assertEqual(task["web"], "http://localhost:40118/")

        checks = [
            "/search?q=type+2+diabetes",
            "/diseases-conditions/diabetes-type-2",
            "/diseases-conditions/atrial-fibrillation",
            "/symptom-checker?region=chest&symptom=chest-pain&age_group=adult&duration=acute",
            "/symptom-checker?region=general&symptom=fatigue&age_group=adult&duration=chronic",
            "/tests-procedures/knee-replacement",
            "/tests-procedures/hip-replacement",
            "/find-a-doctor?specialty=cardiology&location=Jacksonville&language=Spanish",
            "/clinical-trials?q=lung+cancer&phase=Phase+3&status=Recruiting",
            "/drugs-supplements/metformin",
            "/tests-procedures/cabg",
            "/healthy-lifestyle/mediterranean-diet-overview",
            "/find-a-doctor?specialty=neurology&location=Jacksonville",
            "/diseases-conditions/multiple-sclerosis",
            "/clinical-trials?phase=Phase+2&status=Recruiting&location=Rochester",
            "/search?q=breast+cancer",
            "/tests-procedures?category=imaging&letter=M",
            "/departments-centers/transplant",
            "/drugs-supplements?kind=supplement&letter=S",
            "/drugs-supplements/st-johns-wort",
            "/patient-stories/david-parkinsons",
        ]
        for path in checks:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertGreater(len(response.data), 500, path)

        with sqlite3.connect(self.database) as connection:
            facts = {
                "spanish_cardiology_jacksonville": connection.execute(
                    "SELECT COUNT(*) FROM doctor WHERE dept_slug='cardiology' "
                    "AND locations LIKE '%Jacksonville%' AND languages LIKE '%Spanish%'"
                ).fetchone()[0],
                "neurology_jacksonville": connection.execute(
                    "SELECT COUNT(*) FROM doctor WHERE dept_slug='neurology' "
                    "AND locations LIKE '%Jacksonville%'"
                ).fetchone()[0],
                "phase2_recruiting_rochester": connection.execute(
                    "SELECT COUNT(*) FROM clinical_trial WHERE phase='Phase 2' "
                    "AND status='Recruiting' AND locations LIKE '%Rochester%'"
                ).fetchone()[0],
                "alice_saved": connection.execute(
                    "SELECT COUNT(*) FROM saved_item WHERE user_id=1"
                ).fetchone()[0],
            }
        self.assertEqual(
            facts,
            {
                "spanish_cardiology_jacksonville": 1,
                "neurology_jacksonville": 4,
                "phase2_recruiting_rochester": 14,
                "alice_saved": 5,
            },
        )

    def test_guest_auth_logout_and_protected_write(self):
        response = self.client.get("/")
        self.assertIn(b">Log in<", response.data)
        self.assertNotIn(b"Alice Johnson", response.data)
        self.assertEqual(self.client.get("/dev/login/alice_j").status_code, 404)

        response = self.client.post(
            "/save",
            data={
                "kind": "condition",
                "slug": "diabetes-type-2",
                "next": "/diseases-conditions/diabetes-type-2",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login?next=", response.headers["Location"])

        response = self.client.post(
            "/login",
            data={
                "email": "alice.j@test.com",
                "password": "TestPass123!",
                "next": "/diseases-conditions/diabetes-type-2",
            },
        )
        self.assertTrue(
            response.headers["Location"].endswith(
                "/diseases-conditions/diabetes-type-2"
            )
        )

        response = self.client.get("/logout", follow_redirects=True)
        self.assertIn(b">Log in<", response.data)
        self.assertNotIn(b"Alice Johnson", response.data)
        self.assertEqual(self.client.get("/patient-portal").status_code, 302)

    def test_registration_and_authenticated_save(self):
        email = "repair-test@example.com"
        response = self.client.post(
            "/register",
            data={
                "email": email,
                "display_name": "Repair Test",
                "username": "repair_test",
                "password": "StrongPass123!",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Welcome back, Repair Test", response.data)
        response = self.client.post(
            "/save",
            data={
                "kind": "condition",
                "slug": "diabetes-type-2",
                "title": "Injected title",
                "next": "/patient-portal",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Diabetes Type 2", response.data)
        self.assertNotIn(b"Injected title", response.data)

    def test_filters_match_complete_tokens_and_keep_task_counts(self):
        exact_doctors = self.client.get(
            "/find-a-doctor?specialty=neurology&location=Jacksonville"
        )
        self.assertIn(b"4 physicians found", exact_doctors.data)
        partial_doctors = self.client.get(
            "/find-a-doctor?specialty=neurology&location=ville"
        )
        self.assertIn(b"0 physicians found", partial_doctors.data)
        exact_trials = self.client.get(
            "/clinical-trials?phase=Phase+2&status=Recruiting&location=Rochester"
        )
        self.assertIn(b"14 trials found", exact_trials.data)
        partial_trials = self.client.get(
            "/clinical-trials?phase=Phase+2&status=Recruiting&location=chester"
        )
        self.assertIn(b"0 trials found", partial_trials.data)

    def test_registration_rejects_invalid_and_duplicate_identity(self):
        invalid = self.client.post(
            "/register",
            data={
                "email": "not-an-email",
                "display_name": "Invalid",
                "username": "invalid",
                "password": "secret",
            },
        )
        self.assertIn(b"Enter a valid email address", invalid.data)
        duplicate = self.client.post(
            "/register",
            data={
                "email": "unique@example.com",
                "display_name": "Duplicate",
                "username": "alice_j",
                "password": "secret",
            },
        )
        self.assertIn(b"That username is already in use", duplicate.data)
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM user WHERE email IN (?, ?)",
                    ("not-an-email", "unique@example.com"),
                ).fetchone()[0],
                0,
            )

    def test_saved_items_are_real_linked_records_with_canonical_titles(self):
        self.client.post(
            "/register",
            data={
                "email": "saved-test@example.com",
                "display_name": "Saved Test",
                "username": "saved_test",
                "password": "StrongPass123!",
            },
        )
        missing = self.client.post(
            "/save",
            data={"kind": "article", "slug": "invented", "title": "Fake"},
        )
        self.assertEqual(missing.status_code, 404)
        external = self.client.post(
            "/save",
            data={
                "kind": "article",
                "slug": "mediterranean-diet-overview",
                "title": "Injected title",
                "next": "https://example.com/phishing",
            },
        )
        self.assertTrue(
            external.headers["Location"].endswith(
                "/healthy-lifestyle/mediterranean-diet-overview"
            )
        )
        detail = self.client.get("/healthy-lifestyle/mediterranean-diet-overview")
        self.assertIn(b"Remove from portal", detail.data)
        portal = self.client.get("/patient-portal")
        self.assertIn(b'href="/healthy-lifestyle/mediterranean-diet-overview"', portal.data)
        self.assertNotIn(b"Injected title", portal.data)
        removed = self.client.post(
            "/unsave",
            data={
                "kind": "article",
                "slug": "mediterranean-diet-overview",
                "next": "/healthy-lifestyle/mediterranean-diet-overview",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Save article", removed.data)

    def test_appointment_rejects_skips_and_invalid_fields(self):
        with sqlite3.connect(self.database) as connection:
            before = connection.execute(
                "SELECT COUNT(*) FROM appointment_request"
            ).fetchone()[0]

        invalid_step = self.client.get("/appointments/request?step=not-a-number")
        self.assertEqual(invalid_step.status_code, 200)
        self.assertIn(b"Step 1: Select a department", invalid_step.data)
        skipped = self.client.post(
            "/appointments/request",
            data={
                "step": "4",
                "reason": "Skip all validation",
                "next_step": "5",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Step 1: Select a department", skipped.data)
        bad_department = self.client.post(
            "/appointments/request",
            data={"step": "1", "dept": "invented", "location": "Rochester"},
        )
        self.assertIn(b"Choose a valid department", bad_department.data)

        self.client.post(
            "/appointments/request",
            data={"step": "1", "dept": "endocrinology", "location": "Rochester"},
        )
        bad_date = self.client.post(
            "/appointments/request",
            data={
                "step": "2",
                "preferred_date": "2025-01-01",
                "new_or_returning": "unknown",
            },
        )
        self.assertIn(b"Preferred date must be", bad_date.data)
        self.client.post(
            "/appointments/request",
            data={
                "step": "2",
                "preferred_date": "2026-10-15",
                "new_or_returning": "new",
            },
        )
        bad_contact = self.client.post(
            "/appointments/request",
            data={
                "step": "3",
                "patient_name": "Test Patient",
                "patient_email": "invalid",
                "patient_phone": "12",
            },
        )
        self.assertIn(b"Enter a valid email address", bad_contact.data)
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM appointment_request"
                ).fetchone()[0],
                before,
            )

    def test_populated_invalid_prior_step_cannot_finalize_appointment(self):
        valid_state = {
            "dept": "endocrinology",
            "location": "Rochester",
            "preferred_date": "2026-10-15",
            "new_or_returning": "new",
            "patient_name": "Test Patient",
            "patient_email": "test@example.com",
            "patient_phone": "555-1234",
            "insurance": "Aetna",
        }
        with sqlite3.connect(self.database) as connection:
            before = connection.execute(
                "SELECT COUNT(*) FROM appointment_request"
            ).fetchone()[0]

        cases = [
            ({"dept": "invented"}, b"Step 1: Select a department"),
            ({"preferred_date": "not-a-date"}, b"Step 2: Preferred date"),
            ({"patient_email": "invalid"}, b"Step 3: Your information"),
        ]
        for invalid, expected_step in cases:
            with self.subTest(invalid=invalid):
                with self.client.session_transaction() as browser_session:
                    browser_session["appt_request"] = valid_state | invalid
                response = self.client.post(
                    "/appointments/request",
                    data={"step": "4", "reason": "Must not be saved"},
                    follow_redirects=True,
                )
                self.assertIn(expected_step, response.data)

        malformed_next = self.client.get("/login?next=http://[invalid")
        self.assertEqual(malformed_next.status_code, 200)
        self.assertIn(b'value="/patient-portal"', malformed_next.data)
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM appointment_request"
                ).fetchone()[0],
                before,
            )

    def test_guest_appointment_workflow_persists_request(self):
        with sqlite3.connect(self.database) as connection:
            before = connection.execute(
                "SELECT COUNT(*) FROM appointment_request"
            ).fetchone()[0]
        steps = [
            {"step": "1", "dept": "endocrinology", "location": "Rochester", "next_step": "2"},
            {"step": "2", "preferred_date": "2026-10-15", "new_or_returning": "new", "next_step": "3"},
            {
                "step": "3",
                "patient_name": "Test Patient",
                "patient_email": "test@example.com",
                "patient_phone": "555-1234",
                "insurance": "Aetna",
                "next_step": "4",
            },
            {"step": "4", "reason": "Annual diabetes follow-up", "next_step": "5"},
        ]
        response = None
        for form in steps:
            response = self.client.post(
                "/appointments/request", data=form, follow_redirects=True
            )
            self.assertEqual(response.status_code, 200)
        self.assertIn(b"Appointment request received", response.data)
        self.assertIn(b"MAYO-", response.data)
        with sqlite3.connect(self.database) as connection:
            row = connection.execute(
                "SELECT dept_slug, location, preferred_date, patient_email, reason "
                "FROM appointment_request ORDER BY id DESC LIMIT 1"
            ).fetchone()
            after = connection.execute(
                "SELECT COUNT(*) FROM appointment_request"
            ).fetchone()[0]
        self.assertEqual(after, before + 1)
        self.assertEqual(
            row,
            (
                "endocrinology",
                "Rochester",
                "2026-10-15",
                "test@example.com",
                "Annual diabetes follow-up",
            ),
        )

    def test_seed_schema_is_current_and_two_boots_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "mayo_clinic.db"
            shutil.copy2(SEED, database)
            before = sha256(database)
            env = os.environ | {"MAYO_DATABASE_PATH": str(database)}
            command = [
                sys.executable,
                "-c",
                "import app; print(app.app.url_map)",
            ]
            for _ in range(2):
                subprocess.run(
                    command,
                    cwd=SITE,
                    env=env,
                    check=True,
                    stdout=subprocess.DEVNULL,
                )
                self.assertEqual(sha256(database), before)
            subprocess.run(
                [sys.executable, "migrate_seed.py", "--check", str(database)],
                cwd=SITE,
                check=True,
            )

    def test_review_prescreen_does_not_determine_eligibility(self):
        path = '/clinical-trials/SIM-MAYO-001/inquire'
        response = self.client.post(path, data={'patient_name': 'Jordan Lee',
            'patient_email': 'jordan.lee@test.com', 'patient_age': '55',
            'diagnosis_year': '2024', 'prior_treatments': 'None'})
        self.assertEqual(response.status_code, 200)
        with sqlite3.connect(self.database) as c:
            self.assertEqual(c.execute('SELECT eligible_screen FROM trial_inquiry').fetchone()[0], 'needs-review')
        response = self.client.post(path, data={'patient_name': 'Jordan Lee',
            'patient_email': 'invalid', 'patient_age': '-1', 'diagnosis_year': '2024'})
        self.assertEqual(response.status_code, 400)
        with sqlite3.connect(self.database) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM trial_inquiry').fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
