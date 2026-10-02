import importlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


SITE_DIR = Path(__file__).resolve().parents[1]
SEED_DB = SITE_DIR / "instance_seed" / "smartasset.db"


class WebWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory()
        instance = Path(cls.tempdir.name) / "instance"
        instance.mkdir()
        shutil.copy2(SEED_DB, instance / "smartasset.db")
        os.environ["SMARTASSET_INSTANCE_DIR"] = str(instance)
        sys.path.insert(0, str(SITE_DIR))
        cls.site = importlib.import_module("app")
        cls.site.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    @classmethod
    def tearDownClass(cls):
        with cls.site.app.app_context():
            cls.site.db.session.remove()
        cls.tempdir.cleanup()
        os.environ.pop("SMARTASSET_INSTANCE_DIR", None)

    def setUp(self):
        self.client = self.site.app.test_client()

    def test_guest_protection_seeded_login_and_logout(self):
        home = self.client.get("/")
        self.assertNotIn(b"Alice Johnson", home.data)
        protected = self.client.post("/save-calculation", data={
            "calc_slug": "credit-card", "balance": "5000",
            "apr": "22.5", "monthly_payment": "200"
        })
        self.assertEqual(protected.status_code, 302)
        self.assertIn("/login", protected.headers["Location"])
        login = self.client.post("/login", data={
            "email": "alice.j@test.com", "password": "TestPass123!"
        }, follow_redirects=True)
        self.assertEqual(login.status_code, 200)
        self.assertIn(b"Alice Johnson", login.data)
        logout = self.client.get("/logout", follow_redirects=True)
        self.assertIn(b"Signed out", logout.data)
        self.assertNotIn(b"Alice Johnson", logout.data)
        self.assertIn("/login", self.client.get("/account").headers["Location"])
        self.assertEqual(
            self.client.get("/dev/login/alice_j").status_code, 404
        )
        self.assertIn("/login", self.client.get("/account").headers["Location"])

    def test_registration_save_list_and_delete(self):
        email = "workflow-test@example.test"
        registered = self.client.post("/register", data={
            "name": "Workflow Test", "email": email,
            "password": "correct-horse", "state": "TX"
        }, follow_redirects=True)
        self.assertIn(b"Workflow Test", registered.data)
        calculated = self.client.post("/calculators/credit-card", data={
            "balance": "4200", "apr": "18.9", "monthly_payment": "175"
        })
        self.assertIn(b"Paid off in", calculated.data)
        saved = self.client.post("/save-calculation", data={
            "calc_slug": "credit-card", "balance": "4200",
            "apr": "18.9", "monthly_payment": "175",
            "label": "Changed payoff plan"
        }, follow_redirects=True)
        self.assertIn(b"Changed payoff plan", saved.data)
        with self.site.app.app_context():
            user = self.site.User.query.filter_by(email=email).one()
            row = self.site.SavedCalculation.query.filter_by(
                user_id=user.id, label="Changed payoff plan"
            ).one()
            saved_id = row.id
        reopened = self.client.get(
            f"/account/saved/{saved_id}/open", follow_redirects=True
        )
        self.assertIn(b'value="4200"', reopened.data)
        self.assertIn(b'value="18.9"', reopened.data)
        self.assertIn(b'value="175"', reopened.data)
        self.assertIn(b"Paid off in", reopened.data)
        self.client.get("/logout")
        self.client.post("/register", data={
            "name": "Other User", "email": "other-user@example.test",
            "password": "another-password",
        })
        self.assertEqual(
            self.client.get(f"/account/saved/{saved_id}/open").status_code, 404
        )
        self.client.post(f"/account/saved/{saved_id}/delete")
        with self.site.app.app_context():
            self.assertIsNotNone(
                self.site.db.session.get(self.site.SavedCalculation, saved_id)
            )
        self.client.get("/logout")
        self.client.post("/login", data={
            "email": email, "password": "correct-horse"
        })
        deleted = self.client.post(
            f"/account/saved/{saved_id}/delete", follow_redirects=True
        )
        self.assertIn(b"Calculation removed", deleted.data)
        self.assertIn(b"Saved Calculations", deleted.data)
        self.assertNotIn(b"Changed payoff plan", deleted.data)
        self.assertEqual(
            self.client.get(f"/account/saved/{saved_id}/open").status_code, 404
        )

    def test_invalid_calculation_is_not_saved(self):
        self.client.post("/login", data={
            "email": "alice.j@test.com", "password": "TestPass123!"
        })
        with self.site.app.app_context():
            user = self.site.User.query.filter_by(email="alice.j@test.com").one()
            before = self.site.SavedCalculation.query.filter_by(
                user_id=user.id
            ).count()
        response = self.client.post("/save-calculation", data={
            "calc_slug": "credit-card", "balance": "nan",
            "apr": "22.5", "monthly_payment": "200",
        }, follow_redirects=True)
        self.assertIn(b"was not saved", response.data)
        self.assertIn(b"finite number", response.data)
        with self.site.app.app_context():
            after = self.site.SavedCalculation.query.filter_by(
                user_id=user.id
            ).count()
        self.assertEqual(after, before)

    def test_extreme_finite_input_returns_useful_api_error(self):
        response = self.client.post("/api/calculate/retirement", json={
            "current_age": "20", "retire_age": "99",
            "life_age": "100", "growth": "1e308",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"too large to calculate", response.data)

    def test_login_next_stays_on_site(self):
        response = self.client.post(
            "/login?next=https://outside.example/path",
            data={"email": "alice.j@test.com", "password": "TestPass123!"},
        )
        self.assertEqual(response.headers["Location"], "/account")

    def test_advisor_filters(self):
        with self.site.app.app_context():
            for number in range(13):
                self.site.db.session.add(self.site.Advisor(
                    name=f"Filter Test {number:02d}",
                    slug=f"filter-test-{number:02d}",
                    firm="Temporary Test Firm",
                    city="Sacramento",
                    state_abbr="CA",
                    specialty="Tax",
                    min_assets=250000,
                    rating=3.0,
                ))
            self.site.db.session.commit()
        response = self.client.get(
            "/financial-advisor/california"
            "?specialty=Tax&max_min_assets=250000"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Tax", response.data)
        with self.site.app.app_context():
            expected = self.site.Advisor.query.filter(
                self.site.Advisor.state_abbr == "CA",
                self.site.Advisor.specialty == "Tax",
                self.site.Advisor.min_assets <= 250000,
            ).count()
        self.assertGreater(expected, 0)
        self.assertIn(f"{expected} advisors".encode(), response.data)
        self.assertIn(
            b"page=2&amp;specialty=Tax&amp;max_min_assets=250000",
            response.data,
        )
        second_page = self.client.get(
            "/financial-advisor/california"
            "?page=2&specialty=Tax&max_min_assets=250000"
        )
        self.assertIn(b"Filter Test", second_page.data)
        self.assertNotIn(b"Estate Planning", second_page.data)
        invalid = self.client.get(
            "/financial-advisor/california?max_min_assets=-1"
        )
        with self.site.app.app_context():
            all_california = self.site.Advisor.query.filter_by(
                state_abbr="CA"
            ).count()
        self.assertIn(f"{all_california} advisors".encode(), invalid.data)

    def test_task_targets_are_reachable(self):
        targets = [
            "/calculators/credit-card", "/calculators/student-loan",
            "/calculators/savings", "/calculators/income-tax",
            "/calculators/state-tax", "/calculators/paycheck",
            "/calculators/cost-of-living", "/calculators/mortgage",
            "/calculators/retirement", "/calculators/net-worth",
            "/financial-advisor/california", "/financial-advisor/florida",
            "/smartreads/how-the-standard-deduction-works",
            ("/smartreads/"
             "roth-ira-vs-traditional-ira-a-side-by-side-comparison"),
            "/login", "/register",
        ]
        for target in targets:
            with self.subTest(target=target):
                self.assertEqual(self.client.get(target).status_code, 200)

    def test_savings_explains_apy_without_noop_compounding_control(self):
        response = self.client.get("/calculators/savings")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"APY already includes the effect of compounding", response.data)
        self.assertNotIn(b'Compounding frequency', response.data)
        self.assertNotIn(b'name="compound"', response.data)
    def test_review_deduction_used_is_visible(self):
        response = self.client.post('/calculators/income-tax', data={
            'income': '145000', 'filing': 'married', 'pretax_401k': '12000', 'itemized': '20000'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Deduction used', response.data)
        self.assertIn(b'$31,500', response.data)


class TaskContractTests(unittest.TestCase):
    def test_tasks_use_basic_schema_and_real_targets(self):
        allowed = {"web_name", "id", "ques", "web", "upstream_url", "verifier_path", "judge_rubric"}
        tasks = [
            json.loads(line) for line in (SITE_DIR / "tasks.jsonl").read_text().splitlines()
            if line.strip()
        ]
        self.assertGreaterEqual(len(tasks), 15)
        self.assertLessEqual(len(tasks), 20)
        self.assertEqual(len({task["id"] for task in tasks}), len(tasks))
        for task in tasks:
            with self.subTest(task=task["id"]):
                self.assertEqual(set(task), allowed)
                self.assertEqual(task["web"], "http://localhost:40119/")
                self.assertTrue(task["ques"].strip())
                self.assertNotIn("answer", " ".join(task).lower())

        required_topics = {
            "Credit Card Payoff Calculator", "Student Loan Calculator",
            "Savings Calculator", "Federal Income Tax Calculator",
            "State Income Tax Calculator", "Paycheck Calculator",
            "Cost of Living Calculator", "California financial advisor",
            "/smartreads/how-the-standard-deduction-works", "/login",
        }
        combined = "\n".join(task["ques"] + task["upstream_url"] for task in tasks)
        for topic in required_topics:
            self.assertIn(topic, combined)



if __name__ == "__main__":
    unittest.main()
