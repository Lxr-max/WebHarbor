"""No-op, shortcut, wrong-answer, state-mismatch, and pass cases."""

import json
import re
import shutil
import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from verify_lib import TASKS, evaluate

SEED = Path(__file__).resolve().parents[1] / "instance_seed" / "smartasset.db"
BASE = "http://localhost:40103"

PASS_URLS = {
    0: ["/calculators/credit-card?balance=5000&apr=22.5&monthly_payment=200"],
    1: ["/calculators/credit-card"],
    2: ["/calculators/student-loan"],
    3: ["/calculators/savings"],
    4: ["/calculators/income-tax"],
    5: ["/calculators/state-tax"],
    6: ["/calculators/paycheck"],
    7: ["/calculators/cost-of-living"],
    8: ["/calculators/mortgage"],
    9: ["/calculators/retirement"],
    10: ["/financial-advisor/california?specialty=Tax&max_min_assets=250000"],
    11: ["/financial-advisor/florida?specialty=Tax&max_min_assets=250000"],
    12: ["/smartreads/how-the-standard-deduction-works"],
    13: ["/smartreads/roth-ira-vs-traditional-ira-a-side-by-side-comparison"],
    14: ["/register", "/calculators/credit-card", "/account/saved"],
    15: ["/login", "/calculators/savings", "/account"],
    16: [
        "/login",
        "/calculators/cd",
        "/account/saved",
        "/logout",
        "/login?next=/account",
    ],
    17: ["/calculators/net-worth"],
}

PASS_ANSWERS = {
    0: "Paid off in 35 months, total interest $1,810, final payment $10.05.",
    1: "At $150 monthly, payoff is 31 months and interest is $1,029. At $225 monthly, payoff is 19 months and interest is $618.",
    2: "The extra $100 payment saves 27 months and $3,476 of interest.",
    3: "Final balance $78,441, deposits $58,400, interest earned $20,041.",
    4: "The deduction used is the standard deduction of $31,500. Taxable income is $101,500. Federal tax is $12,158. Tax year 2025.",
    5: "Texas is $0. Pennsylvania is $3,135. California is $5,917. Simplified 2025 planning estimate; not a state tax return.",
    6: "Net pay is $2,560 per biweekly paycheck and annual take-home is $66,561.",
    7: "From Austin to New York the equivalent is $149,070. Reversing to Austin the equivalent is $60,542. The direction changes: New York is 56.9% more expensive and Austin is 36.3% less.",
    8: "Monthly principal and interest is $3,103. The total monthly payment is $3,821.",
    9: "Projected nest egg is $1,449,947 and the result is not on track.",
    10: "1 advisor matches: Karen Wright, Robertson Stephens, rating 4.81, minimum assets $100,000.",
    11: "1 advisor matches: Nancy Gonzalez, Carson Group, rating 4.45, minimum assets $100,000.",
    12: "Jeff White, 5 min read. Take the standard deduction or itemize.",
    13: "Jeff White says tax-free growth beats up-front tax deductions.",
    14: "Registered a new account and saved Changed payoff plan. It appears in Saved Calculations.",
    15: "Saved summary: final balance $72,014 and interest $12,014.",
    16: "Removed CD deletion check. After logout, the account page redirects to sign-in.",
    17: "Total assets $758,500, total liabilities $333,500, net worth $425,000.",
}


def traj(answer, paths, page_text=""):
    steps = []
    for i, path in enumerate(paths):
        step = {"step": i, "url": BASE + path}
        if page_text and i == 2:
            step["page_text"] = page_text
        steps.append(step)
    return {"start_url": BASE + "/", "final_answer": answer, "steps": steps}


def mutate(index, path):
    conn = sqlite3.connect(path)
    if index == 14:
        conn.execute(
            """
            INSERT INTO users (email, password_hash, name)
            VALUES ('new.user@example.com', 'x', 'New User')
            """
        )
        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """
            INSERT INTO saved_calcs (user_id, calc_slug, label, inputs_json, summary)
            VALUES (?, 'credit-card', 'Changed payoff plan', ?, ?)
            """,
            (
                uid,
                json.dumps({"balance": "4200", "apr": "18.9", "monthly_payment": "175"}),
                "Paid off in 2y 7m, total interest $1,117",
            ),
        )
    elif index == 15:
        uid = conn.execute(
            "SELECT id FROM users WHERE email='alice.j@test.com'"
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO saved_calcs (user_id, calc_slug, label, inputs_json, summary)
            VALUES (?, 'savings', 'Eight year reserve', ?, ?)
            """,
            (
                uid,
                json.dumps(
                    {
                        "initial": "12000",
                        "monthly_deposit": "500",
                        "years": "8",
                        "apy": "3.8",
                    }
                ),
                "Final balance: $72,014 ($12,014 interest)",
            ),
        )
    elif index == 16:
        uid = conn.execute(
            "SELECT id FROM users WHERE email='bob.smith@test.com'"
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO saved_calcs (user_id, calc_slug, label, inputs_json, summary)
            VALUES (?, 'cd', 'CD deletion check', ?, ?)
            """,
            (
                uid,
                json.dumps({"principal": "10000", "apy": "4.5", "term_months": "12"}),
                "At maturity: $10,450 (450 interest)",
            ),
        )
    conn.commit()
    conn.close()


def contract_literals(value):
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        yield str(value)
    elif isinstance(value, (tuple, list, set, frozenset)):
        for item in value:
            yield from contract_literals(item)
    elif callable(value):
        yield from contract_literals(value.__code__.co_consts)


def literal_words(text):
    return " " + " ".join(re.findall(r"\w+", text.casefold().replace("_", " "))) + " "


def numeric_tokens(text):
    return {
        Decimal(token.replace(",", ""))
        for token in re.findall(r"(?<!\w)\d+(?:,\d{3})*(?:\.\d+)?(?!\w)", text)
    }


class SmartAssetVerifierTests(unittest.TestCase):
    def test_task_schema_and_rules_only_rubrics(self):
        site_dir = SEED.parents[1]
        repo_root = site_dir.parents[1]
        rows = [
            json.loads(line)
            for line in (site_dir / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual([row["id"] for row in rows], [spec["task_id"] for spec in TASKS.values()])
        for index, row in enumerate(rows):
            with self.subTest(task=index, case="schema-no-leak"):
                spec = TASKS[index]
                self.assertEqual(set(row), {
                    "web_name", "id", "ques", "web", "upstream_url",
                    "verifier_path", "judge_rubric",
                })
                self.assertEqual(row["web_name"], row["id"].rsplit("--", 1)[0])
                self.assertEqual(row["verifier_path"], f"sites/{site_dir.name}/verify/verify_{index}.py")
                self.assertTrue((repo_root / row["verifier_path"]).is_file())
                rubric = row["judge_rubric"]
                self.assertTrue(rubric.startswith("FACT CHECKPOINTS:"))
                self.assertEqual(rubric, spec["rubric"])
                expected = list(contract_literals([
                    spec.get("phrases", []), spec.get("numbers", []),
                    [value for _, value in spec.get("bind", [])],
                    spec.get("at_least", (0, []))[1],
                ]))
                callback_values = list(contract_literals([spec.get("pred"), spec.get("state")]))
                answer_numbers = numeric_tokens(" ".join(expected + callback_values + [PASS_ANSWERS[index]]))
                input_numbers = numeric_tokens(row["ques"])
                self.assertFalse(numeric_tokens(rubric) & (answer_numbers - input_numbers))
                for literal in expected:
                    if literal_words(literal) not in literal_words(row["ques"]):
                        self.assertNotIn(literal_words(literal), literal_words(rubric))
                for literal in callback_values:
                    if literal and literal.casefold() not in row["ques"].casefold():
                        for quote, closing in (("\"", "\""), ("'", "'"), ("`", "`"), ("\u201c", "\u201d")):
                            self.assertNotIn(f"{quote}{literal}{closing}".casefold(), rubric.casefold())
                if index == 9:
                    self.assertNotIn("an on-track claim fails", rubric.casefold())

    def test_matrix(self):
        for index in range(18):
            with self.subTest(task=index, case="noop"):
                self.assertFalse(evaluate(index, traj("", ["/"]))["pass"])
            with self.subTest(task=index, case="shortcut"):
                self.assertFalse(
                    evaluate(index, traj(PASS_ANSWERS[index], ["/"]))["pass"]
                )
            with self.subTest(task=index, case="wrong"):
                verdict = evaluate(
                    index,
                    traj("No result. The figure is 0 for Nowhere.", PASS_URLS[index]),
                )
                self.assertFalse(verdict["pass"], verdict)
            stateful = bool(TASKS[index].get("state"))
            with tempfile.TemporaryDirectory() as tmp:
                seed_copy = str(Path(tmp) / "seed.db")
                after = str(Path(tmp) / "after.db")
                shutil.copy(SEED, seed_copy)
                shutil.copy(SEED, after)
                page = "Saved: CD deletion check" if index == 16 else ""
                passed = traj(PASS_ANSWERS[index], PASS_URLS[index], page)
                if stateful:
                    with self.subTest(task=index, case="state-mismatch"):
                        mismatch_traj = (
                            traj(PASS_ANSWERS[index], PASS_URLS[index])
                            if index == 16
                            else passed
                        )
                        mismatch = evaluate(index, mismatch_traj, seed_copy, after)
                        self.assertFalse(mismatch["pass"], mismatch)
                    if index == 16:
                        mutate(index, after)
                        still_there = evaluate(index, passed, seed_copy, after)
                        self.assertFalse(still_there["pass"], still_there)
                        verdict = evaluate(index, passed, seed_copy, seed_copy)
                    else:
                        mutate(index, after)
                        verdict = evaluate(index, passed, seed_copy, after)
                else:
                    verdict = evaluate(index, passed, seed_copy, after)
                with self.subTest(task=index, case="pass"):
                    self.assertTrue(verdict["pass"], verdict)

    def test_swapped_payments(self):
        verdict = evaluate(
            1,
            traj(
                "At $150 monthly, payoff is 19 months and interest is $618. At $225 monthly, payoff is 31 months and interest is $1,029.",
                PASS_URLS[1],
            ),
        )
        self.assertFalse(verdict["pass"], verdict)

    def test_swapped_states(self):
        verdict = evaluate(
            5,
            traj(
                "Texas is $5,917. Pennsylvania is $3,135. California is $0. Simplified 2025 planning estimate; not a state tax return.",
                PASS_URLS[5],
            ),
        )
        self.assertFalse(verdict["pass"], verdict)

    def test_swapped_cities(self):
        verdict = evaluate(
            7,
            traj(
                "From Austin to New York the equivalent is $60,542. Reversing to Austin the equivalent is $149,070. The direction changes.",
                PASS_URLS[7],
            ),
        )
        self.assertFalse(verdict["pass"], verdict)

    def test_zeroed_other_assets(self):
        verdict = evaluate(
            17,
            traj(
                "Total assets $753,500, total liabilities $333,500, net worth $420,000.",
                PASS_URLS[17],
            ),
        )
        self.assertFalse(verdict["pass"], verdict)


if __name__ == "__main__":
    unittest.main()
