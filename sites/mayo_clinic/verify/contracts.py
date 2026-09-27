"""Frozen Mayo Clinic facts. Answers stay in this module."""

import re
import sqlite3

from checks import has_num, has_phrase, near, fold


LIFESTYLE = [
    "healthy weight", "balanced diet", "physically active", "tobacco",
    "alcohol", "stress", "sleep", "vaccination",
]
FATIGUE = [
    "Hypothyroidism", "Anemia", "Depression", "Sleep Apnea", "Chronic Fatigue Syndrome",
]
MS_DOCTORS = ["Adam Clark", "Chelsea Turner", "Hadley Ramirez", "Laila Kennedy"]
IMAGING = [
    "MR Angiography", "MRCP", "MRI Bone", "MRI Brain", "MRI Joint",
    "MRI Pituitary", "MRI Spine", "Mammogram",
]


def _open(path):
    if not path:
        return None
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def state_appointment(initial, after, answer, traj):
    conn = _open(after)
    if conn is None:
        return False, "missing after_state.db"
    try:
        rows = conn.execute(
            """
            SELECT * FROM appointment_request
            WHERE patient_email=? AND preferred_date=?
            """,
            ("test@example.com", "2026-10-15"),
        ).fetchall()
        good = []
        for row in rows:
            if (
                row["dept_slug"] == "endocrinology"
                and row["location"] == "Rochester"
                and row["patient_name"] == "Test Patient"
                and "555" in (row["patient_phone"] or "")
                and "1234" in (row["patient_phone"] or "")
                and (row["insurance"] or "").lower() == "aetna"
                and "diabetes" in (row["reason"] or "").lower()
                and row["confirmation_code"] == "MAYO-277547AF"
            ):
                good.append(row)
        if len(good) != 1:
            return False, f"expected one matching appointment, found {len(good)}"
        if "MAYO-277547AF" not in (answer or ""):
            return False, "answer omits the stored confirmation code"
        return True, "MAYO-277547AF"
    finally:
        conn.close()


def absent_sertraline(answer):
    text = fold(answer)
    if not re.search(
        r"(not|absent|missing|isn't|isnt|except).{0,50}sertraline|sertraline.{0,50}(not|absent|missing|isn't|isnt)",
        text,
    ):
        return False
    for drug in ("anastrozole", "doxorubicin", "trastuzumab"):
        if re.search(
            rf"(not|absent|missing|isn't|isnt).{{0,30}}{drug}|{drug}.{{0,30}}(not|absent|missing|isn't|isnt)",
            text,
        ):
            return False
    return True


def no_byline(answer):
    text = fold(answer)
    if "nutrition" not in text:
        return False
    return any(
        cue in text
        for cue in (
            "no author", "no byline", "not shown", "not listed",
            "does not list", "doesn't list", "without an author", "author is not",
        )
    )


def transplant_one(answer):
    return (
        has_phrase(answer, "SIM-MAYO-036") or has_phrase(answer, "Voxelotor")
    ) and near(answer, "trial", 1, 50)


TASKS = {
    0: {
        "task_id": "Mayo Clinic--0",
        "nav": [r"/diseases-conditions/diabetes-type-2"],
        "at_least": (4, LIFESTYLE),
        "rubric": "FACT CHECKPOINTS: Open Type 2 Diabetes and list four lifestyle changes from its Prevention section. Items that are not in that section fail. Do not stop at three.",
    },
    1: {
        "task_id": "Mayo Clinic--1",
        "nav": [r"/diseases-conditions/atrial-fibrillation"],
        "phrases": ["apixaban", "warfarin", "metoprolol", "amiodarone"],
        "rubric": "FACT CHECKPOINTS: Open Atrial Fibrillation and list the four drugs in the Related Drugs sidebar. A drug from a different condition fails.",
    },
    2: {
        "task_id": "Mayo Clinic--2",
        "nav": [r"/symptom-checker\?(?=[^#\s]*symptom=chest-pain)(?=[^#\s]*age_group=adult)(?=[^#\s]*duration=acute)"],
        "bind": [("pulmonary embolism", "urgent")],
        "rubric": "FACT CHECKPOINTS: Run the symptom checker for an adult with acute chest pain and report the urgency level shown for Pulmonary Embolism. A different symptom or condition fails.",
    },
    3: {
        "task_id": "Mayo Clinic--3",
        "nav": [r"/symptom-checker\?(?=[^#\s]*symptom=fatigue)(?=[^#\s]*age_group=adult)(?=[^#\s]*duration=chronic)"],
        "at_least": (3, FATIGUE),
        "rubric": "FACT CHECKPOINTS: Run the symptom checker for an adult with chronic fatigue and name three possible causes from those results. Causes from a different symptom fail.",
    },
    4: {
        "task_id": "Mayo Clinic--4",
        "nav": [r"/tests-procedures/knee-replacement", r"/tests-procedures/hip-replacement"],
        "phrases": ["Orthopedics"],
        "rubric": "FACT CHECKPOINTS: Open both Knee Replacement and Hip Replacement and report the department that performs both. A department that performs only one of them fails.",
    },
    5: {
        "task_id": "Mayo Clinic--5",
        "nav": [r"/find-a-doctor\?(?=[^#\s]*specialty=cardiology)(?=[^#\s]*location=Jacksonville)(?=[^#\s]*language=Spanish)"],
        "phrases": ["Aaron Bell", "Cardiologist"],
        "rubric": "FACT CHECKPOINTS: Find the Cardiovascular Medicine doctor in Jacksonville who speaks Spanish and report that doctor's full name and listed specialty. Another Jacksonville cardiologist who does not speak Spanish fails.",
    },
    6: {
        "task_id": "Mayo Clinic--6",
        "nav": [r"/clinical-trials/SIM-MAYO-001"],
        "phrases": ["SIM-MAYO-001", "Pembrolizumab"],
        "rubric": "FACT CHECKPOINTS: Open the recruiting simulated Phase 3 lung cancer study and report its SIM-MAYO identifier and intervention. A different phase or condition fails.",
    },
    7: {
        "task_id": "Mayo Clinic--7",
        "nav": [r"/drugs-supplements/metformin"],
        "phrases": ["Type 2 diabetes", "polycystic ovary syndrome", "GI upset", "vitamin B12", "lactic acidosis"],
        "rubric": "FACT CHECKPOINTS: Open Metformin and report the conditions it is listed as treating and its main side effects. Do not substitute another drug's side effects.",
    },
    8: {
        "task_id": "Mayo Clinic--8",
        "nav": [r"/diseases-conditions/coronary-artery-disease", r"/tests-procedures/cabg"],
        "phrases": ["Cardiovascular Medicine"],
        "rubric": "FACT CHECKPOINTS: From Coronary Artery Disease, open the associated CABG procedure and report the department that performs it. A different procedure's department fails.",
    },
    9: {
        "task_id": "Mayo Clinic--9",
        "nav": [r"/appointments/request"],
        "state": state_appointment,
        "rubric": "FACT CHECKPOINTS: Submit the Endocrinology Rochester appointment for Test Patient on 2026-10-15 and report the confirmation code that was stored. A code that was not saved with those details fails.",
    },
    10: {
        "task_id": "Mayo Clinic--10",
        "nav": [r"/healthy-lifestyle/.*/mediterranean-diet-overview|/patient-stories/|mediterranean-diet-overview"],
        "pred": no_byline,
        "rubric": "FACT CHECKPOINTS: Open Mediterranean Diet: A Heart-Healthy Eating Plan. Report its category. The page does not show an author byline; say that no author is displayed rather than inventing one.",
    },
    11: {
        "task_id": "Mayo Clinic--11",
        "nav": [r"/find-a-doctor\?(?=[^#\s]*specialty=neurology)(?=[^#\s]*location=Jacksonville)"],
        "bind": [("jacksonville", 4)],
        "rubric": "FACT CHECKPOINTS: Filter Find a Doctor to Neurology in Jacksonville and report how many physicians match. A count for a different department or campus fails.",
    },
    12: {
        "task_id": "Mayo Clinic--12",
        "nav": [r"/diseases-conditions/multiple-sclerosis"],
        "phrases": ["Neurology"],
        "at_least": (3, MS_DOCTORS),
        "rubric": "FACT CHECKPOINTS: On Multiple Sclerosis, list three doctors under Doctors who treat this and name the linked department. Doctors from a different department fail.",
    },
    13: {
        "task_id": "Mayo Clinic--13",
        "nav": [r"/clinical-trials\?(?=[^#\s]*phase=Phase(?:\+|%20)2)(?=[^#\s]*status=Recruiting)(?=[^#\s]*location=Rochester)"],
        "bind": [("phase", 14)],
        "rubric": "FACT CHECKPOINTS: Filter clinical trials to Phase 2, Recruiting, and Rochester, and report how many simulated studies match. A different phase, status, or campus fails.",
    },
    14: {
        "task_id": "Mayo Clinic--14",
        "nav": [r"/diseases-conditions/breast-cancer"],
        "pred": absent_sertraline,
        "rubric": "FACT CHECKPOINTS: Open Breast Cancer and say which of the named drugs is not in Related Drugs. Marking a drug that is listed as the missing one fails.",
    },
    15: {
        "task_id": "Mayo Clinic--15",
        "nav": [r"/tests-procedures\?(?=[^#\s]*category=imaging)(?=[^#\s]*letter=M)"],
        "phrases": IMAGING,
        "rubric": "FACT CHECKPOINTS: Filter Tests & Procedures to imaging and the letter M, and list every procedure shown. Omitting one, or including a procedure outside that filter, fails.",
    },
    16: {
        "task_id": "Mayo Clinic--16",
        "nav": [r"/departments-centers/transplant"],
        "pred": transplant_one,
        "rubric": "FACT CHECKPOINTS: Open Transplant Center from the departments index and report how many active research trials that page lists, tied to the trial it shows. A count from another department fails.",
    },
    17: {
        "task_id": "Mayo Clinic--17",
        "nav": [r"/drugs-supplements/st-johns-wort"],
        "phrases": ["Many serious drug interactions"],
        "rubric": "FACT CHECKPOINTS: Open St. John's Wort under Herbs & supplements and report the main warning on that page. A different supplement's warning fails.",
    },
    18: {
        "task_id": "Mayo Clinic--18",
        "nav": [r"david-parkinsons"],
        "phrases": ["David", "woodworking"],
        "rubric": "FACT CHECKPOINTS: Open the patient story about deep brain stimulation for Parkinson's and report the patient's first name and the hobby they returned to. A different story fails.",
    },
    19: {
        "task_id": "Mayo Clinic--19",
        "nav": [r"/patient-portal"],
        "phrases": ["MAYO-A1B2C3D4"],
        "bind": [("saved", 5)],
        "rubric": "FACT CHECKPOINTS: Sign in as alice.j@test.com and report how many items Alice has saved and the confirmation code on her existing appointment request. Another patient's code or count fails.",
    },
}
