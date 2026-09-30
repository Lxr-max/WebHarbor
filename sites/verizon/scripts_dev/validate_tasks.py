#!/usr/bin/env python3
"""Measured task audit for the verizon mirror (scripts_dev/validate_tasks.py).

Depth-fix caliber (2026-09-23 standard; identical to the browser harness in
the fix evidence): every task is replayed through the Flask test client and

- atomic  = navigation actions after the home load: link navs (1 each) and
            form actions — each fill/select the agent actively makes = 1
            (pre-checked defaults are NOT counted), each submit = 1.
            Post-submit redirects are the server's doing, not agent actions.
- reads   = perception only; never counted.
- compose = +1 at the end.
- depth   = atomic + compose, gated >= 15.

Also gates, per task: depth >= 15, <= 100 words in `ques`, exactly the
7-key row shape (5 task keys + verifier_path + judge_rubric), no answer
key, no frozen-answer leakage into the task text, and premise resolution
(every value the task asks for is reachable on the walked pages).

Run: python3 scripts_dev/validate_tasks.py
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import sys
import tempfile

SITE_DIR = pathlib.Path(__file__).resolve().parents[1]

# ------------------------------------------------------------------- walker --


class Walker:
    """Test-client walker with an atomic counter (reads never counted)."""

    def __init__(self, db_path: str):
        # fresh app instance per task: drop any cached import of the site
        sys.modules.pop("app", None)
        os.environ["VERIZON_DB_URI"] = f"sqlite:///{db_path}"
        sys.path.insert(0, str(SITE_DIR))
        import app as vz  # noqa: E402
        self.vz = vz
        self.app = vz.app
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        vz.main()
        self.client = self.app.test_client()
        self.atomic = 0
        self.page = ""
        resp = self.client.get("/")              # home load is not counted
        self.page = resp.get_data(as_text=True)

    def nav(self, path):
        resp = self.client.get(path)
        if resp.status_code != 200:
            raise AssertionError(f"nav {path} -> {resp.status_code}")
        self.page = resp.get_data(as_text=True)
        self.atomic += 1

    def form(self, path, fields, defaults=None, method="post"):
        """fields = only the inputs the honest agent actively sets (counted);
        defaults = pre-checked values the browser submits anyway (uncounted)."""
        payload = dict(fields)
        if defaults:
            payload.update(defaults)
        m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', self.page)
        if m:
            payload["csrf_token"] = m.group(1)
        if method == "post":
            resp = self.client.post(path, data=payload, follow_redirects=True)
        else:
            resp = self.client.get(path, query_string=payload, follow_redirects=True)
        if resp.status_code != 200:
            raise AssertionError(f"form {path} -> {resp.status_code}")
        self.page = resp.get_data(as_text=True)
        self.atomic += len(fields) + 1           # fills/selects + submit

    def read(self, needle):
        if needle not in re.sub(r"\s+", " ", self.page):
            raise AssertionError(f"read miss: {needle!r}")

    def count(self, needle):
        return len(re.findall(re.escape(needle), self.page))

    def close(self):
        with self.app.app_context():
            self.vz.db.session.remove()
            self.vz.db.engine.dispose()


def fresh_db(task_id: str) -> str:
    d = tempfile.mkdtemp(prefix=f"verizon-audit-{task_id}-")
    return os.path.join(d, "verizon.db")


def _login(w, email):
    w.nav("/account/login")
    w.form("/account/login", {"email": email, "password": "TestPass123!"})


def _gridwall(w, brand=None, sort=None):
    fields = {}
    if brand is not None:
        fields["brand"] = brand
    if sort is not None:
        fields["sort"] = sort
    w.nav("/smartphones/")
    w.form("/smartphones/", fields, method="get")


def _estimate(w, device, condition, reselect_condition=True):
    w.nav("/trade-in/")
    w.nav("/trade-in/estimate/")
    fields = {"device": device}
    if reselect_condition:
        fields["condition"] = condition
    w.form("/trade-in/estimate/", fields)


# ------------------------------------------------------------------- walks --

def walk_0(w):
    w.nav("/plans/")
    w.form("/plans/", {"lines": "4"}, method="get")
    w.read("$120/month for 4 lines")
    w.read("After AutoPay and $15/mo switch discount")
    w.nav("/smartphones/apple-iphone-18-pro/")
    w.read("Colors available: Burgundy, Black, Silver, Glacier")
    w.nav("/smartphones/apple-iphone-18-pro/configure")
    w.form("/smartphones/apple-iphone-18-pro/configure",
           {"color": "Silver", "storage": "512 GB", "term": "12",
            "protection": "Verizon Mobile Protect"},
           defaults={"plan": "1"})
    w.read("Monthly total: $146.99")
    w.nav("/smartphones/")
    w.read("Google Pixel 10a")
    w.nav("/smartphones/google-pixel-10a/")
    w.read("$13.88/mo")
    w.read("4.2 out of 5 rating")
    w.nav("/trade-in/")
    w.nav("/trade-in/estimate/")
    w.form("/trade-in/estimate/", {"device": "Apple iPhone 17e",
                                   "condition": "Mint"})
    w.read("$300.00")


def walk_1(w):
    w.nav("/prepaid/")
    _estimate(w, "Apple iPhone 17e", "Good")
    _gridwall(w, brand="Samsung", sort="price-desc")
    w.nav("/smartphones/samsung-galaxy-z-fold8/")
    w.nav("/smartphones/samsung-galaxy-z-fold8/configure")
    w.form("/smartphones/samsung-galaxy-z-fold8/configure",
           {"term": "12", "plan": _plan_id(w, "Unlimited")},
           defaults={"protection": ""})


def walk_2(w):
    w.nav("/prepaid/")
    w.read("$30.00/mo")
    w.read("$35.00/mo")
    w.read("Mobile Hotspot: 5 GB")
    w.nav("/plans/")
    w.read("$30/month for 1 line")
    w.nav("/smartphones/")
    w.nav("/smartphones/google-pixel-11/")
    w.nav("/smartphones/google-pixel-11/configure")
    w.form("/smartphones/google-pixel-11/configure",
           {"term": "24", "plan": _plan_id(w, "Unlimited")})
    w.read("Monthly total: $97.49")
    w.nav("/trade-in/")
    w.nav("/trade-in/estimate/")
    w.form("/trade-in/estimate/", {"device": "Google Pixel 10a",
                                   "condition": "Cracked"})
    w.read("$45.00")
    w.form("/trade-in/estimate/", {"condition": "Good"},
           defaults={"device": "Google Pixel 10a"})
    w.read("$160.00")
    w.nav("/support/")
    w.nav("/support/return_policy/")
    w.read("return or exchange of a wireless device")


def walk_3(w):
    _gridwall(w, brand="Samsung", sort="price-asc")
    w.nav("/smartphones/samsung-galaxy-a17-5g/")
    w.nav("/smartphones/samsung-galaxy-a17-5g/configure")
    w.form("/smartphones/samsung-galaxy-a17-5g/configure",
           {"term": "24", "protection": "Wireless Phone Protection"},
           defaults={"storage": "128 GB", "plan": "1"})
    w.nav("/smartphones/")
    w.form("/smartphones/", {"brand": "Apple"}, method="get")
    w.nav("/smartphones/apple-iphone-17e/")
    w.nav("/smartphones/apple-iphone-17e/configure")
    w.form("/smartphones/apple-iphone-17e/configure", {},
           defaults={"color": "Soft Pink", "storage": "256 GB",
                     "term": "36", "protection": "", "plan": "1"})


def walk_4(w):
    w.nav("/smartphones/")
    w.nav("/smartphones/apple-iphone-18-pro/")
    w.nav("/smartphones/apple-iphone-18-pro/configure")
    w.form("/smartphones/apple-iphone-18-pro/configure",
           {"color": "Black", "storage": "1 TB", "term": "48",
            "protection": "Verizon Mobile Protect"})
    w.nav("/smartphones/")
    w.nav("/smartphones/apple-iphone-18-pro-max/")
    _estimate(w, "Apple iPhone 18 Pro", "Mint")


def walk_5(w):
    _gridwall(w, brand="Motorola", sort="price-asc")
    w.nav("/smartphones/motorola-moto-g-2026/")
    w.nav("/smartphones/motorola-moto-g-2026/configure")
    w.form("/smartphones/motorola-moto-g-2026/configure",
           {"protection": "Verizon Mobile Protect"},
           defaults={"storage": "Single capacity", "term": "36", "plan": "1"})
    w.nav("/checkout/")
    w.form("/checkout/", {"name": "Jordan Pratt", "email": "jordan.pratt@example.com",
                          "street": "88 Pine Street", "city": "Seattle",
                          "state": "WA", "zip": "98101"})


def walk_6(w):
    _estimate(w, "Google Pixel 11", "Good")
    w.form("/trade-in/estimate/", {"device": "Motorola moto g - 2026"})
    w.form("/trade-in/estimate/", {"device": "Samsung Galaxy S26 Ultra",
                                   "condition": "Cracked"})
    w.nav("/smartphones/")
    w.nav("/smartphones/samsung-galaxy-s26/")
    w.nav("/smartphones/samsung-galaxy-s26/configure")
    w.form("/smartphones/samsung-galaxy-s26/configure", {"term": "48"},
           defaults={"plan": "1"})


def walk_7(w):
    w.nav("/stores/")
    w.nav("/stores/washington/")
    w.read("55 stores on record in Washington")
    w.nav("/stores/washington/seattle/")
    w.nav("/store/r00000151174/")
    w.read("10:00 AM 06:00 PM")
    w.nav("/store/r00000151174/appointment/")
    w.read("Device trade-in")
    w.nav("/stores/washington/")
    w.nav("/stores/washington/bellevue/")
    w.nav("/store/r00000328070/")
    w.read("Express Pickup Locker")
    w.nav("/stores/washington/")
    w.nav("/stores/washington/tacoma/")
    w.nav("/store/r00000002096/")
    w.read("4009 Tacoma Mall Blvd")
    w.nav("/stores/washington/")
    w.nav("/stores/washington/redmond/")
    w.nav("/store/a00000365426/")
    w.read("Express Pickup In-store")
    w.nav("/stores/washington/")
    w.nav("/stores/washington/everett/")
    w.read("Verizon Company Store — Everett")


def walk_8(w):
    _estimate(w, "Motorola edge - 2026", "Good")
    w.nav("/stores/")
    w.nav("/stores/washington/")
    w.nav("/stores/washington/seattle/")
    w.nav("/store/r00000151174/")
    w.nav("/store/r00000151174/appointment/")
    w.form("/store/r00000151174/appointment/",
           {"name": "Sam Rivera", "email": "sam.rivera@example.com",
            "phone": "206-555-0139", "topic": "Device trade-in",
            "date": "2026-10-06", "time": "02:00 PM"})


def walk_9(w):
    _login(w, "alice.j@test.com")
    w.nav("/account/bills/")
    w.nav("/account/bills/3/")
    w.read("Verizon Mobile Protect — Alice")
    w.read("$17.00")
    w.nav("/account/bills/2/")
    w.read("Verizon Mobile Protect — Alice")
    w.read("$17.00")
    w.nav("/account/bills/1/")
    w.read("Verizon Mobile Protect — Alice")
    w.read("$17.00")
    w.nav("/account/pay/")
    w.form("/account/pay/", {"amount": "50",
                             "method": "Bank account (ACH ending 8891)"})
    w.nav("/account/bills/")
    w.nav("/account/bills/3/")
    w.read("Payments applied")
    w.nav("/account/usage/")
    w.read("31.4 GB")
    w.nav("/account/autopay/")
    w.read("$10/mo per-line discount")


def walk_10(w):
    _login(w, "bob.c@test.com")
    w.nav("/account/bills/")
    w.nav("/account/bills/6/")
    w.read("Wireless Phone Protection — Bob")
    w.read("$9.00")
    w.nav("/account/pay/")
    w.form("/account/pay/", {"method": "Verizon Visa Card ending 0057"})
    w.nav("/account/bills/")
    w.nav("/account/bills/6/")
    w.read("Payments applied")
    w.nav("/account/usage/")
    w.read("18.9 GB")
    w.nav("/account/autopay/")
    w.read("$10/mo per-line discount")
    w.nav("/trade-in/")
    w.nav("/trade-in/estimate/")
    w.form("/trade-in/estimate/", {"device": "Motorola moto g - 2026",
                                   "condition": "Good"})
    w.read("$70.00")


def walk_11(w):
    _login(w, "carol.d@test.com")
    w.nav("/account/autopay/")
    w.form("/account/autopay/", {"autopay": "on", "paper_free": "on"})
    w.nav("/account/bills/")
    w.nav("/account/bills/9/")
    w.read("Verizon Mobile Protect — Tyler")
    w.read("$17.00")
    w.nav("/account/bills/8/")
    w.read("Verizon Mobile Protect — Tyler")
    w.read("$17.00")
    w.nav("/account/usage/")
    w.read("22.1 GB")
    w.nav("/trade-in/")
    w.nav("/trade-in/estimate/")
    w.form("/trade-in/estimate/", {"device": "Google Pixel 10a",
                                   "condition": "Mint"})
    w.read("$210.00")


def walk_12(w):
    _login(w, "alice.j@test.com")
    w.nav("/account/usage/")
    w.read("9.6 GB")
    w.nav("/plans/")
    w.form("/plans/", {"lines": "2"}, method="get")
    w.read("$60/month for 2 lines")
    w.nav("/smartphones/")
    w.nav("/smartphones/google-pixel-11-pro/")
    w.read("Up to 34 hours")
    w.read("3.8 out of 5 rating")
    w.nav("/smartphones/")
    w.nav("/smartphones/apple-iphone-18-pro/")
    w.read("$49.99/mo")
    w.read("Tue, Sep 29 - Fri, Oct 9")
    _estimate(w, "Apple iPhone 18 Pro", "Good")


def walk_13(w):
    _login(w, "dana.k@test.com")
    w.nav("/account/lines/8/change-plan")
    w.form("/account/lines/8/change-plan", {"plan": "4"})
    w.nav("/account/usage/")
    w.nav("/prepaid/")
    w.nav("/account/bills/")
    _estimate(w, "Samsung Galaxy S26 Ultra", "Good")


def walk_14(w):
    _login(w, "alice.j@test.com")
    _gridwall(w, brand="Samsung", sort="price-asc")
    w.nav("/account/")
    w.nav("/account/add-line/")
    w.form("/account/add-line/", {"device": _device_id(w, "Samsung Galaxy A17 5G"),
                                  "nickname": "Mom"},
           defaults={"plan": _plan_id(w, "Simplicity Plan")})
    w.nav("/plans/")
    w.form("/plans/", {"lines": "3"}, method="get")


def walk_15(w):
    w.nav("/support/")
    w.nav("/support/return_policy/")
    _estimate(w, "Samsung Galaxy S26", "Cracked")
    w.form("/trade-in/estimate/", {"device": "Google Pixel 10a",
                                   "condition": "Good"})
    w.nav("/support/")
    w.nav("/support/contact_us/")
    w.nav("/stores/")
    w.nav("/stores/washington/")
    w.nav("/stores/washington/tacoma/")
    w.nav("/store/r00000002096/")


def walk_16(w):
    w.nav("/support/")
    w.nav("/support/troubleshoot/")
    w.form("/support/troubleshoot/",
           {"family": "Google", "issue": "No service or cannot connect to the network"})
    w.form("/support/troubleshoot/",
           {"family": "Apple", "issue": "Battery drains too fast"})
    w.form("/support/troubleshoot/",
           {"family": "Samsung", "issue": "5G speeds are slower than expected"})
    w.nav("/support/")
    w.nav("/support/contact_us/")
    w.nav("/stores/")
    w.nav("/stores/washington/")
    w.nav("/stores/washington/spokane/")


def walk_17(w):
    _login(w, "bob.c@test.com")
    w.nav("/account/orders/")
    w.nav("/account/orders/VZW200038/")
    w.nav("/account/bills/")
    w.nav("/account/usage/")
    _estimate(w, "Google Pixel 11 Pro", "Cracked")
    w.form("/trade-in/estimate/", {"condition": "Mint"},
           defaults={"device": "Google Pixel 11 Pro"})
    w.nav("/account/")


def walk_18(w):
    w.nav("/smartphones/")
    w.nav("/smartphones/apple-iphone-18-pro/")
    w.nav("/smartphones/apple-iphone-18-pro/configure")
    w.form("/smartphones/apple-iphone-18-pro/configure",
           {"color": "Glacier", "storage": "2 TB", "term": "24"},
           defaults={"plan": "1"})
    w.nav("/smartphones/")
    w.nav("/smartphones/samsung-galaxy-s26-ultra/")
    w.nav("/smartphones/samsung-galaxy-s26-ultra/configure")
    w.form("/smartphones/samsung-galaxy-s26-ultra/configure",
           {"color": "Cobalt Violet", "storage": "512 GB", "term": "24"},
           defaults={"plan": "1"})
    w.read("Monthly line")
    w.read("$79.99/mo")
    w.read("$84.16/mo")
    w.read("Monthly total: $164.15")
    w.nav("/trade-in/")
    w.nav("/trade-in/estimate/")
    w.form("/trade-in/estimate/", {"device": "Apple iPhone 18 Pro Max",
                                   "condition": "Good"})
    w.read("$730.00")


def walk_19(w):
    w.nav("/prepaid/")
    w.read("$50.00/mo")
    w.read("Starting at $60.00/mo")
    w.nav("/smartphones/")
    w.nav("/smartphones/samsung-galaxy-a17-5g/")
    w.nav("/smartphones/samsung-galaxy-a17-5g/configure")
    w.form("/smartphones/samsung-galaxy-a17-5g/configure",
           {"term": "24", "plan": _plan_id(w, "Unlimited")},
           defaults={"storage": "128 GB"})
    w.read("Monthly total: $70.41")
    w.nav("/checkout/")
    w.form("/checkout/", {"name": "Rosa Diaz", "email": "rosa.diaz@example.com",
                          "street": "415 Pine St", "city": "Tacoma",
                          "state": "WA", "zip": "98409"})
    w.read("Ships between Wed, Sep 30 - Fri, Oct 9")
    w.nav("/trade-in/")
    w.nav("/trade-in/estimate/")
    w.form("/trade-in/estimate/", {"device": "Motorola razr+ 2026",
                                   "condition": "Good"})
    w.read("$330.00")
    w.form("/trade-in/estimate/", {"condition": "Cracked"},
           defaults={"device": "Motorola razr+ 2026"})
    w.read("$100.00")


WALKS = [walk_0, walk_1, walk_2, walk_3, walk_4, walk_5, walk_6, walk_7,
         walk_8, walk_9, walk_10, walk_11, walk_12, walk_13, walk_14,
         walk_15, walk_16, walk_17, walk_18, walk_19]


def _plan_id(w, name):
    with w.app.app_context():
        plan = w.vz.Plan.query.filter_by(name=name).first()
        return str(plan.id)


def _device_id(w, name):
    with w.app.app_context():
        dev = w.vz.Device.query.filter_by(name=name).first()
        return str(dev.id)


# -------------------------------------------------------------------- audit --

# Frozen premise anchors the walked pages must resolve (per task: the values
# the task text presupposes as reachable, including the r1 N-1 A17 fix).
PREMISES = {
    0: [("/plans/?lines=4", "$120/month for 4 lines"),
        ("/smartphones/apple-iphone-18-pro/", "Colors available: Burgundy, Black, Silver, Glacier"),
        ("/smartphones/google-pixel-10a/", "$13.88/mo"),
        ("/trade-in/estimate/?device=Apple+iPhone+17e&condition=Mint", "$300.00")],
    2: [("/trade-in/estimate/?device=Google+Pixel+10a&condition=Cracked", "$45.00"),
        ("/trade-in/estimate/?device=Google+Pixel+10a&condition=Good", "$160.00"),
        ("/support/return_policy/", "return or exchange of a wireless device")],
    3: [("/smartphones/samsung-galaxy-a17-5g/", "Storage options: 128 GB"),
        ("/smartphones/samsung-galaxy-a17-5g/", "Free shipping by Thursday with new line")],
    4: [("/smartphones/apple-iphone-18-pro/", "Tue, Sep 29 - Fri, Oct 9")],
    7: [("/stores/washington/seattle/", "Verizon Company Store — Seattle Northgate"),
        ("/stores/washington/redmond/", "Victra Redmond"),
        ("/stores/washington/everett/", "Verizon Company Store — Everett"),
        ("/store/r00000151174/appointment/", "Device trade-in")],
    9: [("/account/bills/3/", "Verizon Mobile Protect — Alice"),
        ("/account/bills/2/", "Verizon Mobile Protect — Alice"),
        ("/account/autopay/", "$10/mo per-line discount")],
    10: [("/trade-in/estimate/?device=Motorola+moto+g+-+2026&condition=Good", "$70.00")],
    11: [("/account/bills/9/", "Verizon Mobile Protect — Tyler"),
         ("/account/bills/8/", "Verizon Mobile Protect — Tyler"),
         ("/trade-in/estimate/?device=Google+Pixel+10a&condition=Mint", "$210.00")],
    12: [("/smartphones/google-pixel-11-pro/", "Up to 34 hours"),
         ("/smartphones/apple-iphone-18-pro/", "Tue, Sep 29 - Fri, Oct 9")],
    13: [("/account/lines/8/change-plan", "Unlimited Plus")],
    14: [("/smartphones/?brand=Samsung&sort=price-asc", "Samsung Galaxy A17 5G")],
    17: [("/account/orders/VZW200038/", "Navy Blue")],
    18: [("/smartphones/samsung-galaxy-s26-ultra/", "Up to 30.62 hrs"),
         ("/trade-in/estimate/?device=Apple+iPhone+18+Pro+Max&condition=Good", "$730.00")],
    19: [("/trade-in/estimate/?device=Motorola+razr%2B+2026&condition=Cracked", "$100.00")],
}

# Frozen answer values that must NOT leak into the task text.
NO_LEAK = {
    "128 GB", "Free shipping by Thursday", "$146.99", "$218.33", "$97.49",
    "$49.41", "$98.85", "$71.99", "$54.77", "$48.74", "$370.00",
    "Seattle-Everett", "4009 Tacoma Mall Blvd", "$160.62", "$118.17",
    "$176.46", "$114.08", "(206) 555-", "$79.99", "$164.15", "$70.41",
    "$610.00", "$650.00", "$760.00", "$240.00", "$160.00", "$120.00",
    "$330.00", "$540.00", "$140.00", "$130.00", "$190.00", "$45.00",
    "$300.00", "$730.00", "$210.00", "$70.00", "$100.00", "Tue, Sep 29",
    "$84.16", "3.8 out of 5", "4009 Tacoma Mall",
}


def load_tasks():
    rows = []
    for line in (SITE_DIR / "tasks.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main():
    rows = load_tasks()
    assert len(rows) == 20
    results = []
    failures = []
    for row in rows:
        n = int(row["id"].split("--")[1])
        # shape + word-count + leakage gates
        assert sorted(row) == ["id", "judge_rubric", "ques", "upstream_url",
                               "verifier_path", "web", "web_name"], sorted(row)
        assert "answer" not in row
        words = len(row["ques"].split())
        if words > 100:
            failures.append(f"T{n}: ques has {words} words (>100)")
        for leak in NO_LEAK:
            if leak.lower() in row["ques"].lower():
                failures.append(f"T{n}: task text leaks frozen answer {leak!r}")
        if not (SITE_DIR.parent.parent / row["verifier_path"]).is_file():
            failures.append(f"T{n}: verifier missing: {row['verifier_path']}")
        # measured replay
        db = fresh_db(row["id"])
        w = Walker(db)
        try:
            WALKS[n](w)
            depth = w.atomic + 1
            results.append((row["id"], w.atomic, depth))
            if w.atomic < 15:
                failures.append(f"T{n}: measured atomic {w.atomic} < 15")
            # premise resolution on the walked pages
            for path, needle in PREMISES.get(n, []):
                resp = w.client.get(path)
                page = re.sub(r"\s+", " ", resp.get_data(as_text=True))
                if needle not in page:
                    failures.append(f"T{n}: premise {needle!r} not on {path}")
        except AssertionError as e:
            failures.append(f"T{n}: walk failed: {e}")
        finally:
            w.close()
            shutil.rmtree(os.path.dirname(db), ignore_errors=True)
    print(f"{'task':12} atomic depth")
    for tid, atomic, depth in results:
        print(f"{tid:12} {atomic:6} {depth:5}")
    atomics = [a for _, a, _ in results]
    depths = [d for _, _, d in results]
    print(f"\nmeasured: atomic min={min(atomics)} max={max(atomics)} total={sum(atomics)}")
    print(f"measured: depth  min={min(depths)} max={max(depths)} total={sum(depths)}")
    if failures:
        print("\nAUDIT FAILED:")
        for f in failures:
            print(" !", f)
        return 1
    print("\nAUDIT PASSED: all premises resolved, measured atomic depth >= 15, "
          "no leakage, 7-key shape checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
