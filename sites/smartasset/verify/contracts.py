"""Frozen SmartAsset facts. Answers stay in this module."""

import json
import re
import sqlite3

from checks import after_near, fold, has_num, has_phrase, near


def _open(path):
    if not path:
        return None
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _after_token(text, anchor, value, window, suffix=""):
    """A standalone anchor must be followed by value, optionally then suffix."""
    folded = fold(text)
    needle = fold(anchor)
    for match in re.finditer(rf"(?<!\d){re.escape(needle)}(?!\d)", folded):
        chunk = folded[match.end(): match.end() + window]
        if suffix:
            if re.search(rf"(?<!\d){int(value)}(?!\d)\s*{suffix}", chunk):
                return True
        elif has_num(chunk, value):
            return True
    return False


def _closest_num(text, anchor, window):
    folded = fold(text)
    needle = fold(anchor)
    best = None
    best_dist = None
    for match in re.finditer(re.escape(needle), folded):
        start, end = match.start(), match.end()
        region_start = max(0, start - window)
        region_end = min(len(folded), end + window)
        region = folded[region_start:region_end]
        for num in re.finditer(r"\d+(?:\.\d+)?", region):
            abs_start = region_start + num.start()
            abs_end = region_start + num.end()
            if abs_end <= start:
                dist = start - abs_end
            elif abs_start >= end:
                dist = abs_start - end
            else:
                continue
            if best_dist is None or dist < best_dist:
                best_dist = dist
                raw = num.group()
                best = float(raw) if "." in raw else int(raw)
    return best


def _same_money(found, *expected):
    if found is None:
        return False
    for value in expected:
        if abs(float(found) - float(value)) < 0.02:
            return True
        if abs(float(found) - round(float(value))) < 0.02:
            return True
    return False


def cc_base(answer):
    return (
        has_num(answer, 35)
        and (has_num(answer, 1810) or has_num(answer, 1810.05))
        and has_num(answer, 10.05)
    )


def cc_compare(answer):
    low_months = _after_token(answer, "150", 31, 48, suffix="month")
    low_interest = _after_token(answer, "150", 1029, 80) or _after_token(
        answer, "150", 1028.54, 80
    )
    high_months = _after_token(answer, "225", 19, 48, suffix="month")
    high_interest = _after_token(answer, "225", 618, 80) or _after_token(
        answer, "225", 618.43, 80
    )
    return low_months and low_interest and high_months and high_interest


def loan_savings(answer):
    return has_num(answer, 27) and (has_num(answer, 3476) or has_num(answer, 3475.72))


def fed_tax(answer):
    used_ok = after_near(answer, "used", 31500, 48) or after_near(
        answer, "standard", 31500, 40
    )
    used_wrong = after_near(answer, "used", 20000, 28)
    return (
        used_ok
        and not used_wrong
        and has_num(answer, 101500)
        and has_num(answer, 12158)
        and has_num(answer, 2025)
    )


def _state_hit(answer, name, code, value, window=18):
    return after_near(answer, name, value, window) or _after_token(
        answer, code, value, 12
    )


def state_compare(answer):
    texas = _state_hit(answer, "texas", "tx", 0)
    penn = _state_hit(answer, "pennsylvania", "pa", 3135) or _state_hit(
        answer, "pennsylvania", "pa", 3135.24
    )
    cali = _state_hit(answer, "california", "ca", 5917) or _state_hit(
        answer, "california", "ca", 5917.11
    )
    note = has_phrase(answer, "simplified 2025 planning estimate") and (
        has_phrase(answer, "not a state tax return")
        or has_phrase(answer, "not a tax return")
    )
    return texas and penn and cali and note


def paycheck(answer):
    return (has_num(answer, 2560) or has_num(answer, 2560.05)) and (
        has_num(answer, 66561) or has_num(answer, 66561.4)
    )


def cost_of_living(answer):
    new_york = after_near(answer, "new york", 149070, 36) or after_near(
        answer, "new york", 149069.57, 40
    )
    austin = _after_token(answer, "austin", 60542, 36) or after_near(
        answer, "austin", 60542.2, 36
    )
    explained = (has_num(answer, 56.9) and has_num(answer, 36.3)) or (
        has_phrase(answer, "more") and has_phrase(answer, "less")
    ) or has_phrase(answer, "direction") or has_phrase(answer, "index")
    return new_york and austin and explained


def mortgage(answer):
    principal = _closest_num(answer, "principal", 48)
    if not _same_money(principal, 3103, 3102.51):
        return False
    if has_phrase(answer, "payment"):
        total = _closest_num(answer, "payment", 28)
    else:
        total = _closest_num(answer, "total", 16)
    return _same_money(total, 3821, 3820.84)


def retirement(answer):
    egg = has_num(answer, 1449947) or has_num(answer, 1449946.53)
    folded = fold(answer)
    if re.search(r"on track\W{0,8}yes\b", folded):
        return False
    if re.search(r"\bis on track\b", folded) and "not on track" not in folded:
        return False
    negative = (
        "not on track" in folded
        or "isn't on track" in folded
        or "isnt on track" in folded
        or "off track" in folded
        or re.search(r"on track\W{0,8}no\b", folded) is not None
        or "shortfall" in folded
    )
    return egg and negative


def advisor_count(answer):
    return near(answer, "advisor", 1, 16) or near(answer, "result", 1, 16)


def ira_timing(answer):
    folded = fold(answer)
    upfront = "up-front" in folded or "up front" in folded or "upfront" in folded
    return has_phrase(answer, "jeff white") and has_phrase(answer, "tax-free") and upfront


def net_worth(answer):
    return (
        near(answer, "asset", 758500, 14)
        and near(answer, "liabilit", 333500, 14)
        and near(answer, "net worth", 425000, 20)
    )


def _loads(raw):
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _close(data, key, expected):
    try:
        return abs(float(data.get(key) or 0) - float(expected)) < 0.02
    except (TypeError, ValueError):
        return False


def state_new_payoff(initial, after, answer, traj):
    before = _open(initial)
    conn = _open(after)
    if before is None or conn is None:
        return False, "missing state databases"
    try:
        old_emails = {
            row["email"].lower()
            for row in before.execute("SELECT email FROM users")
        }
        created = [
            row["id"]
            for row in conn.execute("SELECT id, email FROM users")
            if row["email"].lower() not in old_emails
        ]
        if not created:
            return False, "no new account"
        rows = conn.execute(
            """
            SELECT user_id, calc_slug, inputs_json, summary
            FROM saved_calcs WHERE label=?
            """,
            ("Changed payoff plan",),
        ).fetchall()
        owned = [row for row in rows if row["user_id"] in created]
        if len(owned) != 1:
            return False, f"expected one saved payoff plan, found {len(owned)}"
        row = owned[0]
        if row["calc_slug"] != "credit-card":
            return False, "saved row is not the credit-card calculator"
        inputs = _loads(row["inputs_json"])
        if not (
            _close(inputs, "balance", 4200)
            and _close(inputs, "apr", 18.9)
            and _close(inputs, "monthly_payment", 175)
        ):
            return False, f"saved inputs {inputs!r}"
        summary = (row["summary"] or "").replace(",", "")
        if "1117" not in summary and "2y 7m" not in summary:
            return False, "saved summary is not the $4,200 payoff"
        if not has_phrase(answer, "changed payoff plan"):
            return False, "answer does not name the saved calculation"
        return True, "new user saved Changed payoff plan"
    finally:
        before.close()
        conn.close()


def state_alice_savings(initial, after, answer, traj):
    conn = _open(after)
    if conn is None:
        return False, "missing after_state.db"
    try:
        row = conn.execute(
            """
            SELECT sc.calc_slug, sc.inputs_json, sc.summary
            FROM saved_calcs sc
            JOIN users u ON u.id = sc.user_id
            WHERE u.email=? AND sc.label=?
            """,
            ("alice.j@test.com", "Eight year reserve"),
        ).fetchone()
        if row is None or row["calc_slug"] != "savings":
            return False, "Alice has no Eight year reserve savings row"
        inputs = _loads(row["inputs_json"])
        if not (
            _close(inputs, "initial", 12000)
            and _close(inputs, "monthly_deposit", 500)
            and _close(inputs, "years", 8)
            and _close(inputs, "apy", 3.8)
        ):
            return False, f"saved inputs {inputs!r}"
        if not (has_num(answer, 72014) and has_num(answer, 12014)):
            return False, "answer does not report the saved balance and interest"
        return True, "Eight year reserve"
    finally:
        conn.close()


def _observed_text(traj):
    parts = []
    for step in traj.get("steps") or []:
        for key in ("page_text", "observed_text", "text"):
            raw = step.get(key)
            if isinstance(raw, str):
                parts.append(raw)
    return "\n".join(parts)


def _login_after_logout(traj):
    from verify_lib import observed_urls

    saw_logout = False
    for url in observed_urls(traj):
        path = url.split("?", 1)[0]
        if path.rstrip("/").endswith("/logout"):
            saw_logout = True
        elif saw_logout and path.rstrip("/").endswith("/login"):
            return True
    return False


def state_cd_delete(initial, after, answer, traj):
    conn = _open(after)
    if conn is None:
        return False, "missing after_state.db"
    try:
        left = conn.execute(
            """
            SELECT sc.id FROM saved_calcs sc
            JOIN users u ON u.id = sc.user_id
            WHERE u.email=? AND sc.label=?
            """,
            ("bob.smith@test.com", "CD deletion check"),
        ).fetchall()
        if left:
            return False, "CD deletion check is still saved"
        if "cd deletion check" not in fold(_observed_text(traj)):
            return False, "trajectory never showed the saved CD entry"
        if not _login_after_logout(traj):
            return False, "logout was not followed by the sign-in page"
        if not (
            has_phrase(answer, "cd deletion check")
            and (
                has_phrase(answer, "sign")
                or has_phrase(answer, "login")
                or has_phrase(answer, "logged out")
            )
        ):
            return False, "answer does not report the removal and the sign-in redirect"
        return True, "CD entry removed and session ended"
    finally:
        conn.close()


TASKS = {
    0: {
        "task_id": "SmartAsset--0",
        "nav": [r"/calculators/credit-card"],
        "pred": cc_base,
        "rubric": "FACT CHECKPOINTS: Run the credit card payoff calculator at the stated balance, APR, and payment. Report payoff months, total interest, and the final payment shown for that run. A different balance or payment fails.",
    },
    1: {
        "task_id": "SmartAsset--1",
        "nav": [r"/calculators/credit-card"],
        "pred": cc_compare,
        "rubric": "FACT CHECKPOINTS: Run the credit card payoff calculator twice for the same balance and APR, once at each stated monthly payment. Bind each payment to its own payoff months and total interest. Swapping the two payments fails.",
    },
    2: {
        "task_id": "SmartAsset--2",
        "nav": [r"/calculators/student-loan"],
        "pred": loan_savings,
        "rubric": "FACT CHECKPOINTS: Run the student loan calculator with and without the extra monthly payment. Report how many months and how much interest the extra payment saves versus the base term. The base term alone fails.",
    },
    3: {
        "task_id": "SmartAsset--3",
        "nav": [r"/calculators/savings"],
        "numbers": [78441, 58400, 20041],
        "rubric": "FACT CHECKPOINTS: Run the savings calculator with the stated deposit, monthly amount, term, and APY. Report final balance, total deposits, and interest earned for that run.",
    },
    4: {
        "task_id": "SmartAsset--4",
        "nav": [r"/calculators/income-tax"],
        "pred": fed_tax,
        "rubric": "FACT CHECKPOINTS: Run the federal income tax calculator for the stated married filer, 401(k) contribution, and itemized amount. Report the deduction actually applied, taxable income, federal tax, and the tax year named on the calculator. Itemized input that loses to the standard deduction is not the deduction used.",
    },
    5: {
        "task_id": "SmartAsset--5",
        "nav": [r"/calculators/state-tax"],
        "pred": state_compare,
        "rubric": "FACT CHECKPOINTS: Run the state income tax calculator for the same single-filer income in Texas, Pennsylvania, and California. Bind each state to its own estimate and quote the calculator's limitation notice. Swapping states fails.",
    },
    6: {
        "task_id": "SmartAsset--6",
        "nav": [r"/calculators/paycheck"],
        "pred": paycheck,
        "rubric": "FACT CHECKPOINTS: Run the paycheck calculator for the stated Texas single filer, salary, biweekly schedule, 401(k) percent, and health premium. Report net pay per paycheck and annual take-home.",
    },
    7: {
        "task_id": "SmartAsset--7",
        "nav": [r"/calculators/cost-of-living"],
        "pred": cost_of_living,
        "rubric": "FACT CHECKPOINTS: Run the cost-of-living calculator in both directions for the stated salary. Bind the New York equivalent to New York and the Austin equivalent to Austin, and explain what changes when the cities reverse. Swapping the two equivalents fails.",
    },
    8: {
        "task_id": "SmartAsset--8",
        "nav": [r"/calculators/mortgage"],
        "pred": mortgage,
        "rubric": "FACT CHECKPOINTS: Run the mortgage calculator with the stated price, down payment, rate, term, tax, insurance, and HOA. Report monthly principal and interest separately from the total monthly payment. Swapping those two figures fails.",
    },
    9: {
        "task_id": "SmartAsset--9",
        "nav": [r"/calculators/retirement"],
        "pred": retirement,
        "rubric": "FACT CHECKPOINTS: Run the retirement calculator with the stated ages, income, savings, contribution, return, inflation, and replacement rate, leaving other form fields at their displayed defaults. Report the projected nest egg and whether the result says the plan is on track. A conclusion that contradicts the displayed result fails.",
    },
    10: {
        "task_id": "SmartAsset--10",
        "nav": [
            r"/financial-advisor/california\?(?=[^#\s]*specialty=Tax)(?=[^#\s]*max_min_assets=250000)"
        ],
        "phrases": ["Karen Wright", "Robertson Stephens"],
        "numbers": [4.81, 100000],
        "pred": advisor_count,
        "rubric": "FACT CHECKPOINTS: Open the California advisor list filtered to Tax and a maximum account minimum of $250,000. Report how many advisors match and the first advisor's name, firm, rating, and minimum assets. A different state's advisor fails.",
    },
    11: {
        "task_id": "SmartAsset--11",
        "nav": [
            r"/financial-advisor/florida\?(?=[^#\s]*specialty=Tax)(?=[^#\s]*max_min_assets=250000)"
        ],
        "phrases": ["Nancy Gonzalez", "Carson Group"],
        "numbers": [4.45, 100000],
        "pred": advisor_count,
        "rubric": "FACT CHECKPOINTS: Open the Florida advisor list filtered to Tax and a maximum account minimum of $250,000. Say whether anyone matches, and if so give that advisor's name, firm, rating, and minimum assets. An empty-result claim fails when a row is shown.",
    },
    12: {
        "task_id": "SmartAsset--12",
        "nav": [r"/smartreads/how-the-standard-deduction-works"],
        "phrases": ["Jeff White", "standard deduction", "itemize"],
        "bind": [("min", 5)],
        "window": 12,
        "rubric": "FACT CHECKPOINTS: Open the named standard-deduction SmartReads article. Report its author, reading time, and the distinction it draws between the standard deduction and itemizing. The same author on a different article fails.",
    },
    13: {
        "task_id": "SmartAsset--13",
        "nav": [r"/smartreads/roth-ira-vs-traditional-ira-a-side-by-side-comparison"],
        "pred": ira_timing,
        "rubric": "FACT CHECKPOINTS: Open the named Roth versus traditional IRA article. Report its author and the article's stated difference in tax timing between the two IRA types. Author alone, or the standard-deduction article's distinction, fails.",
    },
    14: {
        "task_id": "SmartAsset--14",
        "nav": [r"/register", r"/calculators/credit-card", r"/account"],
        "state": state_new_payoff,
        "rubric": "FACT CHECKPOINTS: Register a new account, run the credit card payoff calculator at the stated inputs, and save it under the requested label. The saved row must belong to the new account and the answer must confirm that label. A pre-seeded account or a different payoff fails.",
    },
    15: {
        "task_id": "SmartAsset--15",
        "nav": [r"/login", r"/calculators/savings", r"/account"],
        "state": state_alice_savings,
        "rubric": "FACT CHECKPOINTS: Sign in as the stated user, run the savings calculator at the stated inputs, save it under the requested label, and report the summary shown for that saved row. A different label, user, or balance fails.",
    },
    16: {
        "task_id": "SmartAsset--16",
        "nav": [r"/login", r"/calculators/cd", r"/account", r"/logout"],
        "state": state_cd_delete,
        "rubric": "FACT CHECKPOINTS: Sign in as the stated user, save the stated CD calculation under the requested label, then remove that entry. After logout, revisiting the account must land on sign-in. The entry still being stored, or a session that survives logout, fails.",
    },
    17: {
        "task_id": "SmartAsset--17",
        "nav": [r"/calculators/net-worth"],
        "pred": net_worth,
        "rubric": "FACT CHECKPOINTS: Run the net worth calculator after changing only the fields the task names, leaving other asset and debt fields at their displayed defaults. Report total assets, total liabilities, and net worth. Zeroing an untouched default, or swapping assets and liabilities, fails.",
    },
}
