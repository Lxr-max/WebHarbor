#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--8.

Car payment calculator: $30,000 car, good credit, $3,000 down — 72-month and
48-month payments + total interest; which term is cheaper per month / costs
less overall; rerun the 72-month case at a custom 9% rate; finally a $40,000
car with excellent credit, $5,000 down, 60 months (monthly + APR used).
Read-only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_price, contains_all,
                        contains_any, check_trajectory_identity, check_read_only)

TASK_ID = "Cars.com--8"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_read_only(judge, initial_db, after_db)

    judge.check("nav_calculator", navigated_to(traj, "/car-loan-calculator/"),
                "required: the payment calculator")

    # 72-month case: $513/mo, $6,843 total interest
    judge.check("answer_72_monthly", contains_price(answer, 513),
                "expected the 72-month monthly payment $513")
    judge.check("answer_72_interest", contains_any(answer, ["6,843", "6843"]),
                "expected the 72-month total interest $6,843")
    # 48-month case: $720/mo, $4,494 total interest
    judge.check("answer_48_monthly", contains_price(answer, 720),
                "expected the 48-month monthly payment $720")
    judge.check("answer_48_interest", contains_any(answer, ["4,494", "4494"]),
                "expected the 48-month total interest $4,494")
    # cheaper per month = 72-month; costs less overall = 48-month
    judge.check("answer_cheaper_per_month",
                contains_any(answer, ["72"]) and contains_any(answer, ["cheaper per month", "lower monthly", "cheaper monthly"]),
                "expected: the 72-month term is cheaper per month")
    judge.check("answer_less_overall",
                contains_any(answer, ["48"]) and contains_any(answer, ["less overall", "costs less", "overall"]),
                "expected: the 48-month term costs less overall")
    # rerun at 9%: $542/mo
    judge.check("answer_9pct_monthly", contains_price(answer, 542),
                "expected the 9% rerun monthly payment $542")
    # $40,000 / excellent / $5,000 down / 60 months: $747/mo at 5.5% APR
    judge.check("answer_40k_monthly", contains_price(answer, 747),
                "expected the $40,000 monthly payment $747")
    judge.check("answer_40k_apr", contains_any(answer, ["5.5"]),
                "expected the APR used: 5.5%")


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
