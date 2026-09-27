"""No-op, shortcut, wrong-answer, state-mismatch, and pass cases."""

import shutil
import sqlite3
import tempfile
import unittest
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


class MayoVerifierTests(unittest.TestCase):
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
