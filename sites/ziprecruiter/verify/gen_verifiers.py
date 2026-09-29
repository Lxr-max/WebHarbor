#!/usr/bin/env python3
"""gen_verifiers.py — emits verify_N.py from the frozen reviewer spec table.

The checked-in verify_N.py files ARE the contract; regenerate only when a
task text changes (and re-freeze the ground truth from fresh honest walks).

Ground truth provenance: every value below was transcribed LIVE from the
reviewer's two independent Playwright rounds on the review container
(wh-ziprecruiter-review, seed md5 6d6830746bd74d5b19b91c983dec0c3c), with
the two rounds producing identical facts per task. Nothing is read from
tasks.jsonl and no answer key ships outside the verifiers.
"""
import textwrap

HEADER = '''#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--{n} (ziprecruiter).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
Playwright rounds on the review container wh-ziprecruiter-review, seed md5
6d6830746bd74d5b19b91c983dec0c3c) — never read from tasks.jsonl.
{note}
Usage: python3 verify_{n}.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_number, check_answer_number_absent, check_answer_ordered,
    check_answer_phrase, check_answer_regex, check_read_only,
    check_only_tables_changed, check_row_matches, check_rows_added,
    check_rows_removed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, run_verifier,
)

TASK_ID = "ZipRecruiter--{n}"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
{nav}
    # -- answer ground truth --
{ans}
{db}
if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
'''

FOOTER_DB_READONLY = """
    check_read_only(judge, initial, after)
"""
FOOTER_DB_NONE = ""


def nav_block(gates):
    out = []
    for name, pat in gates:
        out.append(f'    check_visited_path(judge, traj, "{name}", r"{pat}")')
    return "\n".join(out) if out else "    pass  # navigation gates live in the answer anchors"


def ans_block(checks):
    out = []
    for c in checks:
        kind = c[0]
        if kind == "phrase":
            out.append(f'    check_answer_phrase(judge, answer, "{c[1]}", "{c[2]}")')
        elif kind == "any":
            items = ", ".join(f'"{x}"' for x in c[2])
            out.append(f'    check_answer_any(judge, answer, "{c[1]}", [{items}])')
        elif kind == "number":
            val = f'"{c[2]}"' if isinstance(c[2], str) else repr(c[2])
            out.append(f'    check_answer_number(judge, answer, "{c[1]}", {val})')
        elif kind == "number_absent":
            val = f'"{c[2]}"' if isinstance(c[2], str) else repr(c[2])
            out.append(f'    check_answer_number_absent(judge, answer, "{c[1]}", {val})')
        elif kind == "ordered":
            items = ", ".join(f'"{x}"' for x in c[2])
            out.append(f'    check_answer_ordered(judge, answer, "{c[1]}", [{items}])')
        elif kind == "at_least":
            items = ", ".join(f'"{x}"' for x in c[2])
            out.append(f'    check_answer_count_at_least(judge, answer, "{c[1]}", [{items}], {c[3]})')
        elif kind == "regex":
            out.append(f'    check_answer_regex(judge, answer, "{c[1]}", r"{c[2]}")')
        elif kind == "absent":
            out.append(f'    check_answer_absent(judge, answer, "{c[1]}", "{c[2]}")')
    return "\n".join(out)


def db_block(stateful):
    if not stateful:
        return FOOTER_DB_READONLY
    lines = []
    for c in stateful:
        kind = c[0]
        if kind == "only_tables":
            items = ", ".join(f'"{x}"' for x in c[1])
            lines.append(f'    check_only_tables_changed(judge, initial, after, {{{items}}})')
        elif kind == "added":
            lines.append(f'    check_rows_added(judge, initial, after, "{c[1]}", {c[2]})')
        elif kind == "removed":
            lines.append(f'    check_rows_removed(judge, initial, after, "{c[1]}", {c[2]})')
        elif kind == "row":
            lines.append(f'    check_row_matches(judge, after, "{c[1]}", {c[2]}, "{c[3]}")')
    return "\n" + "\n".join(lines) + "\n"


# ==================================================================== SPECS ===
S = 'http://localhost:49115'

SPECS = {
0: dict(
 note="Task premise defect (see the review report): the industry/headquarters\nasks in T2-style company facts resolve here; T0's company (YO AI Labs)\ncarries all three fields, so T0 is fully answerable.",
 nav=[
   ("serp_swe_sf", r"/jobs-search\?search=software\+engineer.*location=San\+Francisco"),
   ("remote_filter", r"remote=remote"),
   ("job_detail", r"/Job/Software-Engineer-Open-Source-Contributions-Remote.*jid=032e0b0150231b0d"),
   ("company", r"/co/YO-AI-Labs"),
   ("days5", r"days=5"),
 ],
 ans=[
   ("number", "base_count", 22),
   ("number", "remote_count", 1),
   ("phrase", "remote_first_title", "Software Engineer - Open Source Contributions - Remote"),
   ("phrase", "remote_first_co", "YO AI Labs"),
   ("phrase", "remote_first_pay", "$50 - $100/hr"),
   ("any", "loc_type", ["remote", "no location-type"]),
   ("phrase", "employment", "Full Time"),
   ("phrase", "posted", "3 days ago"),
   ("phrase", "industry", "Computing Infrastructure Providers, Data Processing, Web Hosting"),
   ("phrase", "size", "201 - 500 Employees"),
   ("phrase", "hq", "Abu Dhabi, Abu Dhabi, AE"),
   ("number", "days5_count", 13),
   ("phrase", "days5_first", "Forward Deployed Software Engineer"),
   ("phrase", "days5_posted", "7 hours ago"),
   ("regex", "days5_quick_negated", "not a quick apply|no quick apply|isn.t a quick apply"),
 ],
 db=[],
),
1: dict(
 note="",
 nav=[
   ("serp_rn_ny", r"/jobs-search\?search=registered\+nurse.*location=New\+York"),
   ("quick_filter", r"apply=quick"),
   ("days5_filter", r"days=5"),
   ("job_detail", r"/Job/Registered-Nurse-Gastroenterology.*jid="),
   ("reset", r"reset|location=New\+York,?\s*NY?(&|$)|/jobs-search\?search=registered\+nurse&location=New\+York"),
 ],
 ans=[
   ("number", "base", 24),
   ("number", "quick", 9),
   ("number", "quick5", 5),
   ("phrase", "first_title", "Registered Nurse - Gastroenterology"),
   ("phrase", "first_co", "Park Ave Gastroenterology"),
   ("phrase", "first_city", "Huntington, NY"),
   ("phrase", "first_pay", "$40 - $50/hr"),
   ("phrase", "posted", "23 hours ago"),
   ("phrase", "employment", "Part Time"),
   ("phrase", "f1", "CareOne"),
   ("phrase", "f1_pay", "$39 - $57/hr"),
   ("phrase", "f2", "BAYADA Home Health Care"),
   ("phrase", "f3", "Care One Enterprise"),
   ("phrase", "f4", "Care Options for Kids"),
   ("phrase", "f5", "Atlantic Rehabilitation Institute"),
   ("phrase", "highest", "$85K - $89K/yr"),
 ],
 db=[],
),
2: dict(
 note="PREMISE DEFECT (documented in the review report): the task asks for the\nlisting company's industry and the company's headquarters, but Matter\nFamily Office carries neither in the seed, so neither page shows them.\nThe verifier pins everything that DOES resolve; a fix must either seed\nthose fields or re-anchor the asks, then re-freeze this verifier.",
 nav=[
   ("serp_den", r"/jobs-search\?search=accountant.*location=Denver"),
   ("smin_filter", r"smin=70000"),
   ("job_detail", r"/Job/Senior-Accountant.*jid=3770eecfc82fcf30"),
   ("company", r"/co/Matter-Family-Office"),
   ("days10", r"days=10"),
 ],
 ans=[
   ("number", "base", 12),
   ("number", "smin70", 4),
   ("phrase", "first_title", "Senior Accountant"),
   ("phrase", "first_co", "Matter Family Office"),
   ("phrase", "first_pay", "$80K - $100K/yr"),
   ("phrase", "employment", "Full Time"),
   ("number", "open_jobs", 1),
   ("number", "days10", 10),
   ("phrase", "days10_posted", "posted today"),
 ],
 db=[],
),
3: dict(
 note="UI DEFECT (documented in the review report): the employment-type filter\npanel cannot combine two types in a real browser (the app reads only the\nfirst `et` query param). The combined count (29) is reachable only via\nthe combined URL `et=part_time,per_diem`, which this verifier requires.\nA fix must make the panel submit both values, then this gate still\nholds. The first PT/combined listing shows NO pay anywhere — the honest\nanswer reports that; the verifier accepts the no-pay phrasing.",
 nav=[
   ("serp_nurse", r"/jobs-search\?search=nurse"),
   ("pt_filter", r"et=part_time"),
   ("combined", r"et=part_time,per_diem|et=per_diem&.*et=part_time|et=part_time&.*et=per_diem"),
   ("quick", r"apply=quick"),
   ("exp_none", r"exp=none"),
 ],
 ans=[
   ("number", "base", 124),
   ("number", "pt", 27),
   ("phrase", "pt_first_title", "Part-Time Licensed Practical Nurse (LPN) - West Hartford"),
   ("phrase", "pt_first_co", "GameDay Men's Health - West Hartford"),
   ("phrase", "pt_first_city", "West Hartford, CT"),
   ("any", "pt_first_pay", ["no pay", "not shown", "no salary", "none shown"]),
   ("number", "pt_pd", 29),
   ("any", "ptpd_first_pay", ["no pay", "not shown", "no salary", "none shown"]),
   ("number", "quick", 78),
   ("phrase", "quick_first_co", "Supplemental Health Care"),
   ("phrase", "quick_first_loc", "Oregon, WI"),
   ("number", "quick_none", 0),
 ],
 db=[],
),
4: dict(
 note="",
 nav=[
   ("serp_swe", r"/jobs-search\?search=software\+engineer(&|$|&)"),
   ("senior", r"exp=senior"),
   ("job_detail", r"/Job/Senior-Software-Engineer.*jid="),
   ("company", r"/co/Burnt"),
   ("junior", r"exp=junior"),
   ("none", r"exp=none"),
 ],
 ans=[
   ("number", "base", 76),
   ("number", "senior", 12),
   ("phrase", "senior_first", "Senior Software Engineer"),
   ("phrase", "senior_co", "Burnt"),
   ("phrase", "senior_pay", "$144K - $190K/yr"),
   ("phrase", "loc", "San Francisco, CA"),
   ("phrase", "posted", "2 days ago"),
   ("regex", "quick_negated", "not a quick apply|no quick apply|isn.t a quick apply"),
   ("number", "company_open", 1),
   ("number", "junior", 1),
   ("phrase", "junior_first", "Software Engineer I & II"),
   ("phrase", "junior_pay", "$55K - $95K/yr"),
   ("number", "none", 2),
 ],
 db=[],
),
5: dict(
 note="",
 nav=[
   ("serp_atl", r"/jobs-search\?search=truck\+driver.*location=Atlanta"),
   ("page2", r"page=2"),
   ("job_detail", r"/Job/CDL-A-Truck-Driver.*jid="),
   ("quick", r"apply=quick"),
 ],
 ans=[
   ("number", "base", 21),
   ("number", "pages", 2),
   ("phrase", "p1_first", "CDL A Truck Driver"),
   ("phrase", "p1_co", "Dollar General Fleet"),
   ("phrase", "p1_pay", "$100K/yr"),
   ("phrase", "p2_first", "CDL A Truck Driver - Regional"),
   ("phrase", "p2_co", "Epes Transport Systems, Inc."),
   ("phrase", "p2_pay", "$66K - $96K/yr"),
   ("phrase", "mr_posted", "18 days ago"),
   ("phrase", "mr_pay", "$100K/yr"),
   ("phrase", "mr_employment", "Full Time"),
   ("number", "quick", 10),
   ("phrase", "quick_pay", "$26 - $28/hr"),
   ("number", "n_cities", 7),
   ("phrase", "city1", "Acworth"),
   ("phrase", "city2", "Austell"),
   ("phrase", "city3", "East Point"),
   ("phrase", "city4", "Lawrenceville"),
   ("phrase", "city5", "Marietta"),
   ("phrase", "city6", "Mcdonough"),
 ],
 db=[],
),
6: dict(
 note="",
 nav=[
   ("serp_dal", r"/jobs-search\?search=warehouse.*location=Dallas"),
   ("quick", r"apply=quick"),
   ("job_detail", r"/Job/Forklift-Operator.*jid=024f93e335f888a9"),
   ("company", r"/co/Proman-Staffing"),
   ("second", r"/Job/Cold-Environment-Warehouse-Packers"),
   ("days5", r"days=5"),
 ],
 ans=[
   ("number", "base", 17),
   ("number", "quick", 8),
   ("phrase", "first_title", "Forklift Operator"),
   ("phrase", "first_co", "Proman Staffing"),
   ("phrase", "first_city", "Fort Worth, TX"),
   ("phrase", "first_pay", "$16.25 - $19.25/hr"),
   ("phrase", "posted", "8 hours ago"),
   ("phrase", "employment", "Full Time"),
   ("number", "company_open", 1),
   ("phrase", "second_title", "Cold Environment Warehouse Packers"),
   ("phrase", "second_pay", "$13.50 - $14.50/hr"),
   ("phrase", "second_city", "Grand Prairie, TX"),
   ("number", "days5", 10),
 ],
 db=[],
),
7: dict(
 note="Navigation caveat (review report): the location-scoped company jobs page\n(/co/<slug>/Jobs/-in-<City>,ST) has NO inbound link on the mirror — the\nhonest agent reaches it by the upstream URL pattern; this verifier gates\non the URL itself.",
 nav=[
   ("serp_swe_sf", r"/jobs-search\?search=software\+engineer.*location=San\+Francisco"),
   ("job_detail", r"/Job/Forward-Deployed-Software-Engineer.*jid=5f4b2c55241a752f"),
   ("company", r"/co/Veritus$"),
   ("sf_jobs", r"/co/Veritus/Jobs/-in-San-Francisco,CA"),
   ("days5", r"days=5"),
 ],
 ans=[
   ("phrase", "title", "Forward Deployed Software Engineer"),
   ("phrase", "co", "Veritus"),
   ("phrase", "loc", "San Francisco, CA"),
   ("phrase", "loc_type", "On-site"),
   ("phrase", "employment", "Full Time"),
   ("phrase", "posted", "7 hours ago"),
   ("phrase", "badge", "New"),
   ("regex", "badge_quick_negated", "not a quick apply|no quick apply|isn.t a quick apply"),
   ("phrase", "industry", "Offices of Mental Health Practitioners"),
   ("phrase", "size", "11 - 50 Employees"),
   ("phrase", "platform", "OpenAI"),
   ("phrase", "hq", "New York, NY"),
   ("phrase", "website", "veritussolutions.com"),
   ("number", "open_jobs", 11),
   ("number", "sf_jobs", 1),
   ("number", "days5", 13),
   ("phrase", "days5_posted", "7 hours ago"),
 ],
 db=[],
),
8: dict(
 note="Same navigation caveat as T7 for the New York company jobs page.",
 nav=[
   ("serp_rn_ny", r"/jobs-search\?search=registered\+nurse.*location=New\+York"),
   ("job_detail", r"/Job/Registered-Nurse.*jid="),
   ("company", r"/co/CareOne$"),
   ("ny_jobs", r"/co/CareOne/Jobs/-in-New-York,NY"),
   ("quick", r"apply=quick"),
   ("second", r"/Job/Private-Duty-Registered-Nurse"),
   ("breakroom_co", r"/co/BAYADA-Home-Health-Care"),
 ],
 ans=[
   ("phrase", "title", "Registered Nurse"),
   ("phrase", "co", "CareOne"),
   ("phrase", "city", "East Brunswick, NJ"),
   ("phrase", "pay", "$39 - $57/hr"),
   ("phrase", "employment", "Full Time"),
   ("phrase", "posted", "21 days ago"),
   ("number", "company_open", 1),
   ("number", "ny_jobs", 0),
   ("number", "quick", 9),
   ("phrase", "quick_first_co", "Park Ave Gastroenterology"),
   ("phrase", "quick_first_pay", "$40 - $50/hr"),
   ("phrase", "second_title", "Private Duty Registered Nurse (RN)"),
   ("phrase", "second_city", "Hoboken, NJ"),
   ("phrase", "second_pay", "$35 - $45/hr"),
   ("number", "breakroom_score", "6.87"),
   ("number", "breakroom_count", 257),
 ],
 db=[],
),
9: dict(
 note="",
 nav=[
   ("serp_swe_sf", r"/jobs-search\?search=software\+engineer.*location=San\+Francisco"),
   ("job_detail", r"/Job/Forward-Deployed-Software-Engineer"),
   ("company", r"/co/Veritus"),
   ("remote", r"remote=remote"),
   ("days5", r"days=5"),
   ("browse", r"/browse$"),
   ("letter_s", r"/browse/titles/S"),
   ("title_page", r"/Jobs/software-engineer$"),
   ("salary", r"/Salaries/software-engineer-Salary"),
   ("nearby", r"/Job/Full-Stack-Software-Engineer--PRO-Team"),
 ],
 ans=[
   ("number", "base", 22),
   ("phrase", "loc_type", "On-site"),
   ("phrase", "employment", "Full Time"),
   ("phrase", "posted", "7 hours ago"),
   ("phrase", "industry", "Offices of Mental Health Practitioners"),
   ("phrase", "hq", "New York, NY"),
   ("number", "remote", 1),
   ("number", "days5", 1),
   ("number", "roles", 76),
   ("number", "avg", "147,524"),
   ("number", "avg_hour", "70.92"),
   ("number", "p25", "120,000"),
   ("phrase", "nearby_title", "Full-Stack Software Engineer -- PRO Team"),
   ("phrase", "nearby_co", "Viome Life Sciences"),
 ],
 db=[],
),
10: dict(
 note="PREMISE WEAKNESS (review report): the nearby job's company (Quick 2 Hire)\ncarries no industry in the seed; the honest answer reports that absence.\nThe RN title/salary/nearby/top-cities/related/search chain is otherwise\nfully answerable.",
 nav=[
   ("browse", r"/browse$"),
   ("letter_r", r"/browse/titles/R"),
   ("rn_title", r"/Jobs/registered-nurse$"),
   ("salary", r"/Salaries/registered-nurse-Salary"),
   ("nearby", r"/Job/Registered-Nurse-Stepdown"),
   ("company", r"/co/Quick-2-Hire"),
   ("serp_rn_ny", r"/jobs-search\?search=registered\+nurse.*location=New\+York"),
   ("quick", r"apply=quick"),
 ],
 ans=[
   ("number", "roles", 74),
   ("number", "avg", "92,525"),
   ("number", "avg_hour", "44.48"),
   ("number", "median", "92,525"),
   ("phrase", "nearby_title", "Registered Nurse Stepdown"),
   ("phrase", "nearby_co", "Quick 2 Hire"),
   ("phrase", "nearby_loc", "On-site"),
   ("phrase", "nearby_pay", "$47 - $50/hr"),
   ("any", "co_industry", ["no industry", "not shown", "none"]),
   ("phrase", "city1", "San Mateo County, CA"),
   ("number", "city1_avg", "129,338"),
   ("phrase", "city2", "Mineral, VA"),
   ("number", "city2_avg", "127,705"),
   ("phrase", "city3", "Portola Valley, CA"),
   ("number", "city3_avg", "122,470"),
   ("phrase", "related", "Manager Interventional Radiology Rn"),
   ("number", "related_avg", "147,291"),
   ("number", "rn_ny", 24),
   ("number", "rn_ny_quick", 9),
   ("phrase", "quick_first_co", "Park Ave Gastroenterology"),
   ("phrase", "quick_first_pay", "$40 - $50/hr"),
 ],
 db=[],
),
11: dict(
 note="Navigation caveat (review report): the city salary variant\n(/Salaries/<title>-Salary-in-<City>,ST) has NO inbound link on the mirror;\nthe honest agent reaches it by the upstream URL pattern.",
 nav=[
   ("browse", r"/browse$"),
   ("letter_s", r"/browse/titles/S"),
   ("swe_title", r"/Jobs/software-engineer$"),
   ("salary_national", r"/Salaries/Software-Engineer-Salary$|/Salaries/software-engineer-Salary$"),
   ("salary_sf", r"/Salaries/Software-Engineer-Salary-in-San-Francisco,CA|/Salaries/software-engineer-Salary-in-San-Francisco,CA"),
   ("serp", r"/jobs-search\?search=software\+engineer(&|$)"),
   ("senior", r"exp=senior"),
   ("remote", r"remote=remote"),
   ("job_detail", r"/Job/Senior-Staff-Software-Engineer"),
 ],
 ans=[
   ("number", "avg_year", "147,524"),
   ("number", "avg_hour", "70.92"),
   ("number", "median", "147,524"),
   ("number", "p10", "95,500"),
   ("number", "p90", "205,000"),
   ("number", "sf_avg_year", "173,808"),
   ("number", "sf_avg_hour", "83.56"),
   ("number", "sf_median", "173,808"),
   ("number", "sf_p25", "141,400"),
   ("number", "national_jobs", 76),
   ("number", "senior", 12),
   ("number", "senior_remote", 1),
   ("phrase", "first_title", "Senior/Staff Software Engineer, Platform"),
   ("phrase", "first_co", "AIDA Recruitment"),
   ("phrase", "first_pay", "$150K - $350K/yr"),
   ("phrase", "first_posted", "6 days ago"),
   ("phrase", "city1", "Soledad, CA"),
   ("number", "city1_avg", "220,681"),
   ("phrase", "city2", "Portola Valley, CA"),
   ("number", "city2_avg", "205,618"),
 ],
 db=[],
),
12: dict(
 note="Same navigation caveat as T11 for the Denver salary variant. The days-10\nand quick-apply filters stack in the honest walk (the SERP keeps days=10\nwhen quick apply is added).",
 nav=[
   ("browse", r"/browse$"),
   ("letter_a", r"/browse/titles/A"),
   ("acct_title", r"/Jobs/accountant$"),
   ("salary_national", r"/Salaries/accountant-Salary$|/Salaries/Accountant-Salary$"),
   ("serp_den", r"/jobs-search\?search=accountant.*location=Denver"),
   ("smin", r"smin=70000"),
   ("job_detail", r"/Job/Senior-Accountant.*jid=3770eecfc82fcf30"),
   ("days10", r"days=10"),
   ("quick", r"apply=quick"),
   ("salary_denver", r"/Salaries/Accountant-Salary-in-Denver,CO"),
 ],
 ans=[
   ("number", "avg_year", "68,326"),
   ("number", "avg_hour", "32.85"),
   ("number", "median", "68,326"),
   ("number", "p75", "78,500"),
   ("number", "bands_ge15", 4),
   ("number", "den_jobs", 12),
   ("number", "den_70", 4),
   ("phrase", "first_title", "Senior Accountant"),
   ("phrase", "first_co", "Matter Family Office"),
   ("phrase", "first_pay", "$80K - $100K/yr"),
   ("phrase", "posted", "yesterday"),
   ("phrase", "employment", "Full Time"),
   ("number", "days10", 10),
   ("number", "quick", 2),
   ("number", "denver_avg", "70,327"),
   ("number", "denver_p25", "55,100"),
 ],
 db=[],
),
13: dict(
 note="Blog taxonomy defect (review report): the seeded subcategory set\n(tips-advice, professional-development) does not match the article data\n(students, work-life), so the Tips & Advice category shows 0 articles\nand the honest count is 0.",
 nav=[
   ("blog", r"/blog/$"),
   ("trends", r"/blog/category/career-advice/trends/"),
   ("article", r"/blog/salary_exp/"),
   ("tips", r"/blog/category/career-advice/tips-advice/"),
   ("serp_da", r"/jobs-search\?search=data\+analyst.*location=Seattle"),
   ("days5", r"days=5"),
 ],
 ans=[
   ("number", "blog_cats", 7),
   ("number", "trends_count", 5),
   ("phrase", "article_title", "4 Top Industry Insights to Fuel Your Job Search"),
   ("phrase", "author", "The ZipRecruiter Editors"),
   ("phrase", "published", "2023-03-07"),
   ("at_least", "insights", ["There Are More Jobs", "Jobs Offer More Flexibility",
                             "Workplaces Want to Be More Diverse", "Perks and Benefits Are a Priority"], 4),
   ("any", "hottest", ["There Are More Jobs", "more jobs"]),
   ("any", "other_trends", ["Job News Roundup", "Who's Hiring Now", "COVID-19 Resources for Job Seekers"]),
   ("number", "tips_count", 0),
   ("number", "da_sea", 20),
   ("number", "da_days5", 4),
   ("phrase", "first_co", "DKMRBH Inc"),
   ("phrase", "first_pay", "$50 - $55/hr"),
 ],
 db=[],
),
14: dict(
 note="",
 nav=[
   ("blog", r"/blog/$"),
   ("veterans", r"/blog/category/career-advice/veterans/"),
   ("article1", r"/blog/job-search-tips-for-veterans/"),
   ("article2", r"/blog/the-12-best-job-industries-for-veterans/"),
   ("serp_ele", r"/jobs-search\?search=electrician.*location=Houston"),
   ("days5", r"days=5"),
   ("quick", r"apply=quick"),
 ],
 ans=[
   ("number", "veterans_count", 2),
   ("phrase", "a1_title", "Job Search Tips Every Military Veteran Should Know"),
   ("phrase", "a1_author", "Julia Pollak"),
   ("phrase", "a1_published", "2020-11-10"),
   ("phrase", "a1_updated", "2022-06-16"),
   ("at_least", "a1_tips", ["Where should I look for work",
                            "What should I do if I don't have any work experience",
                            "What kinds of industries should I explore",
                            "How much should I expect to earn"], 4),
   ("phrase", "a2_title", "The 12 Best Job Industries For Veterans"),
   ("phrase", "a2_author", "Kat Boogaard"),
   ("any", "a2_published", ["2017-10-20"]),
   ("phrase", "hot_title", "Dressing for Hot Weather Job Interviews"),
   ("phrase", "hot_cat", "The Hiring Process"),
   ("phrase", "hot_author", "Nicole Cavazos"),
   ("phrase", "hot_published", "2018-08-24"),
   ("number", "ele_hou", 17),
   ("number", "ele_days5", 4),
   ("number", "ele_quick", 4),
   ("phrase", "first_co", "FALCON CONTROL SYSTEMS"),
   ("phrase", "first_pay", "$20 - $40/hr"),
   ("phrase", "first_posted", "19 hours ago"),
 ],
 db=[],
),
15: dict(
 note="Stateful: exactly one non-benchmark user (+profile), one application and\none application event for the first quick-apply Dallas warehouse job\n(Forklift Operator, jid 024f93e335f888a9). The verifier pins the delta\nshape, not the agent-chosen email.",
 nav=[
   ("register", r"/authn/register"),
   ("serp", r"/jobs-search\?search=warehouse.*location=Dallas"),
   ("quick", r"apply=quick"),
   ("job_detail", r"/Job/Forklift-Operator.*jid=024f93e335f888a9"),
   ("apply_done", r"/apply/done/024f93e335f888a9"),
   ("applications", r"/jobseeker/applications"),
 ],
 ans=[
   ("phrase", "confirm_heading", "Application sent"),
   ("phrase", "job_title", "Forklift Operator"),
   ("phrase", "job_co", "Proman Staffing"),
   ("phrase", "status", "Applied"),
   ("phrase", "timeline_note", "1-Click Application submitted"),
   ("number", "base", 17),
   ("number", "quick", 8),
   ("number", "saved_start", 0),
 ],
 db=[
   ("only_tables", ["users", "profiles", "applications", "application_events"]),
   ("added", "users", 1),
   ("added", "profiles", 1),
   ("added", "applications", 1),
   ("added", "application_events", 1),
   ("row", "SELECT COUNT(*) FROM users WHERE is_benchmark=0", (), "new_user_nonbenchmark"),
   ("row", "SELECT COUNT(*) FROM applications a JOIN jobs j ON j.id=a.job_id WHERE j.jid='024f93e335f888a9'", (), "app_for_proman_forklift"),
   ("row", "SELECT COUNT(*) FROM application_events WHERE note='1-Click Application submitted' AND occurred_at='2026-09-29'", (), "app_event_row"),
 ],
),
16: dict(
 note="PREMISE DEFECT (review report): no saved listing has a gastroenterology\nemployer; the intended listing is the Manhattan Urology job at New York\nHealth (the first Manhattan row), which is what the contributor's own\nwalker unsaves. This verifier pins that target.",
 nav=[
   ("login", r"/authn/login"),
   ("profile", r"/jobseeker/profile"),
   ("saved", r"/jobseeker/saved-jobs"),
   ("alerts", r"/jobseeker/alerts"),
 ],
 ans=[
   ("phrase", "headline", "Registered Nurse, BSN — 6 years ICU"),
   ("number", "years", 6),
   ("phrase", "location", "Brooklyn, NY"),
   ("phrase", "s1_title", "Registered Nurse (RN) - Bilingual Spanish/English (Urology)"),
   ("phrase", "s1_co", "New York Health"),
   ("phrase", "s1_city", "Manhattan, NY"),
   ("phrase", "s1_pay", "$52/hr"),
   ("phrase", "s2_title", "Registered Nurse IV Drip - Park Slope"),
   ("phrase", "s2_city", "Brooklyn, NY"),
   ("phrase", "s2_pay", "$52 - $54/hr"),
   ("phrase", "s3_title", "Registered Nurse (RN)"),
   ("phrase", "s3_co", "New York Cancer & Blood Specialists"),
   ("phrase", "s3_pay", "$52/hr"),
   ("phrase", "remaining2", "Brooklyn"),
   ("phrase", "remaining2b", "Manhattan"),
   ("phrase", "alert_term", "licensed practical nurse"),
   ("phrase", "alert_loc", "Brooklyn, NY"),
   ("phrase", "alert_freq", "Daily"),
   ("phrase", "alert1_term", "registered nurse"),
   ("phrase", "alert1_loc", "New York, NY"),
 ],
 db=[
   ("only_tables", ["saved_jobs", "job_alerts"]),
   ("removed", "saved_jobs", 1),
   ("added", "job_alerts", 1),
   ("row", "SELECT COUNT(*) FROM saved_jobs WHERE user_id=(SELECT id FROM users WHERE email='alice.j@test.com')", (), "alice_saved_count"),
   ("row", "SELECT COUNT(*) FROM saved_jobs s JOIN jobs j ON j.id=s.job_id JOIN companies c ON c.id=j.company_id WHERE c.slug='New-York-Health' AND s.user_id=(SELECT id FROM users WHERE email='alice.j@test.com')", (), "urology_unsaved"),
   ("row", "SELECT COUNT(*) FROM job_alerts WHERE term='licensed practical nurse' AND location='Brooklyn, NY' AND frequency='daily' AND user_id=(SELECT id FROM users WHERE email='alice.j@test.com')", (), "new_alert_row"),
 ],
),
17: dict(
 note="Stateful: one saved job removed (the most recent save — the YO AI Labs\nOpen Source listing), one weekly data-engineer alert created.",
 nav=[
   ("login", r"/authn/login"),
   ("profile", r"/jobseeker/profile"),
   ("applications", r"/jobseeker/applications"),
   ("job_detail", r"/Job/Software-Engineer.*jid=19d6f9232eedc0f5|/c/JOLT/"),
   ("resume", r"/jobseeker/resume"),
   ("saved", r"/jobseeker/saved-jobs"),
   ("alerts", r"/jobseeker/alerts"),
 ],
 ans=[
   ("phrase", "app_title", "Software Engineer"),
   ("phrase", "app_co", "JOLT"),
   ("phrase", "app_city", "San Francisco, CA"),
   ("phrase", "applied_at", "2026-09-21"),
   ("phrase", "status", "Interviewing"),
   ("phrase", "tl1", "2026-09-21"),
   ("phrase", "tl1_note", "1-Click Application submitted"),
   ("phrase", "tl2", "2026-09-23"),
   ("phrase", "tl2_note", "The employer viewed your application"),
   ("phrase", "tl3", "2026-09-27"),
   ("phrase", "tl3_note", "The employer invited you to schedule a phone screen"),
   ("phrase", "job_pay", "$125K - $135K/yr"),
   ("phrase", "job_loc_type", "On-site"),
   ("phrase", "job_posted", "17 days ago"),
   ("phrase", "resume_title", "Software Engineer — Full Stack"),
   ("phrase", "resume_updated", "2026-09-19"),
   ("phrase", "resume_complete", "complete"),
   ("phrase", "resume_summary", "Backend-leaning full-stack engineer; Python, Go, Postgres."),
   ("phrase", "resume_exp", "JOLT"),
   ("at_least", "resume_skills", ["Python", "Go", "PostgreSQL", "React"], 4),
   ("phrase", "remaining", "JOLT"),
   ("phrase", "alert_term", "data engineer"),
   ("phrase", "alert_loc", "Seattle, WA"),
   ("phrase", "alert_freq", "Weekly"),
 ],
 db=[
   ("only_tables", ["saved_jobs", "job_alerts"]),
   ("removed", "saved_jobs", 1),
   ("added", "job_alerts", 1),
   ("row", "SELECT COUNT(*) FROM job_alerts WHERE term='data engineer' AND location='Seattle, WA' AND frequency='weekly' AND user_id=(SELECT id FROM users WHERE email='bob.c@test.com')", (), "bob_new_alert"),
   ("row", "SELECT COUNT(*) FROM saved_jobs WHERE user_id=(SELECT id FROM users WHERE email='bob.c@test.com')", (), "bob_saved_after"),
 ],
),
18: dict(
 note="Stateful: dana's resume row changes (QuickBooks/2yrs appended, 7 skills\ntotal, updated_at moves to the mirror date). No row-count change.",
 nav=[
   ("login", r"/authn/login"),
   ("profile", r"/jobseeker/profile"),
   ("resume", r"/jobseeker/resume"),
   ("applications", r"/jobseeker/applications"),
   ("alerts", r"/jobseeker/alerts"),
 ],
 ans=[
   ("phrase", "resume_title", "Senior Accountant (CPA)"),
   ("phrase", "resume_summary", "CPA with 8 years across public accounting and industry; month-end close, audit readiness, NetSuite."),
   ("phrase", "exp1_role", "Senior Accountant"),
   ("phrase", "exp1_co", "Matter Family Office"),
   ("phrase", "exp1_dates", "2022-04"),
   ("phrase", "exp2_role", "Staff Accountant II"),
   ("phrase", "exp2_co", "Caribou Financial"),
   ("phrase", "exp2_dates", "2019-06"),
   ("phrase", "edu1", "BS, Accounting"),
   ("phrase", "edu1_school", "Metro State Denver"),
   ("phrase", "edu2", "CPA license"),
   ("at_least", "skills", ["NetSuite", "Month-end close", "GAAP", "Excel", "Audit prep", "SQL"], 6),
   ("phrase", "new_skill", "QuickBooks"),
   ("number", "skill_count", 7),
   ("phrase", "updated_at", "2026-09-29"),
   ("phrase", "app_title", "Senior Accountant"),
   ("phrase", "app_co", "Matter Family Office"),
   ("phrase", "app_city", "Denver, CO"),
   ("phrase", "app_status", "Withdrawn"),
   ("phrase", "app_tl1", "2026-09-20"),
   ("phrase", "app_tl2", "2026-09-22"),
   ("phrase", "app_tl3", "2026-09-25"),
   ("phrase", "alert1", "accountant"),
   ("phrase", "alert1_loc", "Denver, CO"),
   ("phrase", "alert1_freq", "Daily"),
   ("phrase", "alert2", "remote bookkeeping"),
   ("phrase", "alert2_loc", "Anywhere"),
   ("phrase", "alert2_freq", "Weekly"),
 ],
 db=[
   ("only_tables", ["resumes"]),
   ("row", "SELECT COUNT(*) FROM resumes r JOIN users u ON u.id=r.user_id WHERE u.email='dana.k@test.com' AND r.skills LIKE '%QuickBooks%'", (), "quickbooks_added"),
   ("row", "SELECT json_array_length(r.skills) FROM resumes r JOIN users u ON u.id=r.user_id WHERE u.email='dana.k@test.com'", (), "skills_len"),
   ("row", "SELECT COUNT(*) FROM resumes r JOIN users u ON u.id=r.user_id WHERE u.email='dana.k@test.com' AND r.updated_at='2026-09-29'", (), "updated_at_moved"),
 ],
),
19: dict(
 note="",
 nav=[
   ("serp_chi", r"/jobs-search\?search=teacher.*location=Chicago"),
   ("job_detail", r"/Job/Travel-Special-Education-Teacher"),
   ("company", r"/co/"),
   ("serp_la", r"/jobs-search\?search=receptionist.*location=Los\+Angeles"),
   ("days5", r"days=5"),
   ("browse", r"/browse$"),
   ("letter_r", r"/browse/titles/R"),
   ("title_page", r"/Jobs/receptionist$"),
   ("salary", r"/Salaries/receptionist-Salary"),
 ],
 ans=[
   ("number", "teacher_chi", 21),
   ("phrase", "first_title", "Travel Special Education Teacher"),
   ("phrase", "first_posted", "2 days ago"),
   ("phrase", "first_employment", "Other"),
   ("phrase", "first_pay", "$2.3K - $2.5K/wk"),
   ("phrase", "co_industry", "Recruiting and Staffing Services"),
   ("number", "co_open", 1),
   ("number", "rec_la", 19),
   ("number", "rec_days5", 9),
   ("phrase", "rec_first_title", "EXPERIENCED Dental Office Treatment Coordinator / Receptionist"),
   ("phrase", "rec_first_co", "Restore Dental"),
   ("phrase", "rec_first_pay", "$20 - $35/hr"),
   ("phrase", "r_title1", "Receptionist"),
   ("phrase", "r_title2", "Registered Nurse"),
   ("number", "r_count", 2),
   ("number", "salary_avg", "37,057"),
 ],
 db=[],
),
}


def main():
    for n, spec in SPECS.items():
        note = spec.get("note", "")
        code = HEADER.format(n=n, note=note, nav=nav_block(spec["nav"]),
                             ans=ans_block(spec["ans"]),
                             db=db_block(spec.get("db", [])))
        with open(f"verify_{n}.py", "w") as f:
            f.write(code)
    print(f"emitted {len(SPECS)} verifiers")


if __name__ == "__main__":
    main()
