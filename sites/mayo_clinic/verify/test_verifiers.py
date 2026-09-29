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

SEED = Path(__file__).resolve().parents[1] / "instance_seed" / "mayo_clinic.db"
BASE = "http://localhost:40102"

PASS_URLS = {
    0: ["/diseases-conditions/diabetes-type-2"],
    1: ["/diseases-conditions/atrial-fibrillation"],
    2: ["/symptom-checker?region=chest&symptom=chest-pain&age_group=adult&duration=acute"],
    3: ["/symptom-checker?region=general&symptom=fatigue&age_group=adult&duration=chronic"],
    4: ["/tests-procedures/knee-replacement", "/tests-procedures/hip-replacement"],
    5: ["/find-a-doctor?specialty=cardiology&location=Jacksonville&language=Spanish"],
    6: ["/clinical-trials/SIM-MAYO-001"],
    7: ["/drugs-supplements/metformin"],
    8: ["/diseases-conditions/coronary-artery-disease", "/tests-procedures/cabg"],
    9: ["/appointments/request"],
    10: ["/healthy-lifestyle/mediterranean-diet-overview"],
    11: ["/find-a-doctor?specialty=neurology&location=Jacksonville"],
    12: ["/diseases-conditions/multiple-sclerosis"],
    13: ["/clinical-trials?phase=Phase+2&status=Recruiting&location=Rochester"],
    14: ["/search?q=breast+cancer", "/diseases-conditions/breast-cancer"],
    15: ["/tests-procedures?category=imaging&letter=M"],
    16: ["/departments-centers/transplant"],
    17: ["/drugs-supplements?kind=supplement", "/drugs-supplements/st-johns-wort"],
    18: ["/patient-stories/david-parkinsons"],
    19: ["/patient-portal"],
}

PASS_ANSWERS = {
    0: "Prevention lists maintaining a healthy weight, eating a balanced diet, staying physically active, and avoiding tobacco.",
    1: "Related drugs: apixaban, warfarin, metoprolol, and amiodarone.",
    2: "Pulmonary Embolism is marked urgent.",
    3: "Possible causes include Hypothyroidism, Anemia, and Depression.",
    4: "Orthopedics performs both knee and hip replacement.",
    5: "Aaron Bell, M.D., specialty Cardiologist.",
    6: "SIM-MAYO-001 uses Pembrolizumab + Carboplatin + Pemetrexed.",
    7: "Metformin treats Type 2 diabetes and polycystic ovary syndrome. Side effects include GI upset, vitamin B12 deficiency, and rare lactic acidosis.",
    8: "CABG is performed by Cardiovascular Medicine.",
    9: "Confirmation code MAYO-277547AF.",
    10: "Category Nutrition. No author byline is shown.",
    11: "4 physicians match in Jacksonville neurology.",
    12: "Doctors include Adam Clark, Chelsea Turner, and Hadley Ramirez. The department is Neurology.",
    13: "14 Phase 2 recruiting studies in Rochester.",
    14: "The drug that is not listed is sertraline.",
    15: "MR Angiography, MRCP, MRI Bone, MRI Brain, MRI Joint, MRI Pituitary, MRI Spine, and Mammogram.",
    16: "Transplant Center lists 1 trial, SIM-MAYO-036 (Voxelotor).",
    17: "The main warning is Many serious drug interactions.",
    18: "The patient's first name is David and he returned to woodworking.",
    19: "Alice has 5 saved items. Her appointment confirmation is MAYO-A1B2C3D4.",
}


def traj(answer, paths):
    return {
        "start_url": BASE + "/",
        "final_answer": answer,
        "steps": [{"step": i, "url": BASE + path} for i, path in enumerate(paths)],
    }


def mutate(index, path):
    if index != 9:
        return
    conn = sqlite3.connect(path)
    conn.execute(
        """
        INSERT INTO appointment_request
        (dept_slug, location, preferred_date, patient_name, patient_email, patient_phone,
         reason, insurance, new_or_returning, status, confirmation_code, created_at)
        VALUES ('endocrinology', 'Rochester', '2026-10-15', 'Test Patient', 'test@example.com',
                '555-1234', 'Annual diabetes follow-up', 'Aetna', 'new', 'requested',
                'MAYO-277547AF', '2026-09-01')
        """
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


class MayoVerifierTests(unittest.TestCase):
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
                if index == 10:
                    for outcome in ("no author", "no byline", "does not show an author"):
                        self.assertNotIn(outcome, rubric.casefold())

    def test_matrix(self):
        for index in range(20):
            with self.subTest(task=index, case="noop"):
                self.assertFalse(evaluate(index, traj("", ["/"]))["pass"])
            with self.subTest(task=index, case="shortcut"):
                self.assertFalse(evaluate(index, traj(PASS_ANSWERS[index], ["/"]))["pass"])
            with self.subTest(task=index, case="wrong"):
                verdict = evaluate(index, traj("No page matched. The department is Nowhere.", PASS_URLS[index]))
                self.assertFalse(verdict["pass"], verdict)
            stateful = bool(TASKS[index].get("state"))
            with tempfile.TemporaryDirectory() as tmp:
                seed_copy = str(Path(tmp) / "seed.db")
                after = str(Path(tmp) / "after.db")
                shutil.copy(SEED, seed_copy)
                shutil.copy(SEED, after)
                if stateful:
                    with self.subTest(task=index, case="state-mismatch"):
                        verdict = evaluate(index, traj(PASS_ANSWERS[index], PASS_URLS[index]), seed_copy, after)
                        self.assertFalse(verdict["pass"], verdict)
                    mutate(index, after)
                with self.subTest(task=index, case="pass"):
                    verdict = evaluate(index, traj(PASS_ANSWERS[index], PASS_URLS[index]), seed_copy, after)
                    self.assertTrue(verdict["pass"], verdict)

    def test_present_drug_is_not_the_missing_one(self):
        verdict = evaluate(
            14,
            traj("Anastrozole is not in Related Drugs.", PASS_URLS[14]),
        )
        self.assertFalse(verdict["pass"], verdict)


if __name__ == "__main__":
    unittest.main()
