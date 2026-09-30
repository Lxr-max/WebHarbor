#!/usr/bin/env python3
"""append_rubrics.py — append verifier_path + judge_rubric to ../tasks.jsonl.

The five contributor keys stay byte-identical (each output row is the
original line with the two keys appended); no ``answer`` key is ever
written. The rubrics are pure English grading rules with no ground-truth
anchors (the answers live only in the frozen verifiers). Idempotent.

Run: python3 append_rubrics.py
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = HERE.parent / "tasks.jsonl"

# ---------------------------------------------------------------------------
# Judge rubrics: pure rules, no answer values. Every rubric states the
# checkpoints the agent must open and the facts it must report exactly as
# the opened pages show them.
# ---------------------------------------------------------------------------
RUBRICS = {
"ZipRecruiter--0":
 "FACT CHECKPOINTS: Search software engineer jobs in San Francisco, CA from the home page, "
 "apply the Remote filter, open the first remaining listing, open its company profile, "
 "return to the search, clear the remote filter, set the date filter to within 5 days. "
 "Report the initial result count, the remote-only count, the first remote listing's title, "
 "company and pay, its location type, employment type and posted age, the company's "
 "industry, size and headquarters, and the within-5-days count with the first job's title, "
 "posted age and quick-apply status. PASS requires every count and field exactly as shown "
 "on the opened pages. FAIL on any wrong count, wrong company, wrong pay or an empty answer.",
"ZipRecruiter--1":
 "FACT CHECKPOINTS: Search registered nurse jobs in New York, NY, apply the quick-apply-only "
 "filter, add the within-5-days date filter, open the first remaining listing, return to the "
 "unfiltered search. Report the base count, the quick-apply count, the combined count, the "
 "first combined listing's title, company, city and hourly pay, its posted age and employment "
 "type, the states the first five unfiltered listings cover with each listing's company and "
 "pay, and the highest-paying listing among them with its pay. PASS requires every value "
 "exactly as shown. FAIL on any wrong count, wrong state, wrong pay or an empty answer.",
"ZipRecruiter--2":
 "FACT CHECKPOINTS: Search accountant jobs in Denver, CO, set the minimum-salary filter to "
 "$70,000, open the first remaining listing, open its company profile, return to the search, "
 "clear the salary filter and apply the within-10-days date filter. Report the base count, "
 "the filtered count, the first listing's title, company and pay range, its employment type, "
 "the company's industry and headquarters as its profile shows them (state clearly if the "
 "page shows neither), how many open jobs the company lists, and the within-10-days count "
 "with the first job's posted age. PASS requires every resolvable value exactly as shown and "
 "an honest statement where the page shows no data. FAIL on invented values or wrong counts.",
"ZipRecruiter--3":
 "FACT CHECKPOINTS: Search nurse jobs nationwide with the location empty, filter employment "
 "type to Part Time, add Per Diem for the combined filter, clear the employment filters, "
 "apply quick-apply-only, then add the no-experience-needed experience filter. Report the "
 "nationwide count, the Part Time count, the first Part Time listing's title, company and "
 "city (and its pay exactly if the page shows one, otherwise state that none is shown), the "
 "combined Part Time + Per Diem count, the quick-apply count with the first listing's company "
 "and location, and the count satisfying quick apply plus no experience. PASS requires every "
 "count exactly as the filtered pages show them. FAIL on any wrong count or invented pay.",
"ZipRecruiter--4":
 "FACT CHECKPOINTS: Search software engineer jobs nationwide, apply the senior-level-and-above "
 "experience filter, open the first remaining listing, open its company profile, switch the "
 "experience filter to junior level, then to no experience needed. Report the nationwide "
 "count, the senior count, the first senior listing's title, company and pay, its location, "
 "posted age and quick-apply status, how many open jobs its company lists, the junior count "
 "with the first listing's title and pay, and the no-experience count. PASS requires every "
 "value exactly as shown on the opened pages. FAIL on any wrong count or wrong pay.",
"ZipRecruiter--5":
 "FACT CHECKPOINTS: Search truck driver jobs in Atlanta, GA, go to result page 2 and back to "
 "page 1, open the most recently posted listing on page 1, apply the quick-apply-only filter, "
 "then return to the unfiltered results across every page. Report the total count and how "
 "many result pages the site offers, page 1's first listing's title, company and pay, page 2's "
 "first listing's title, company and pay, the most recent listing's posted age, pay and "
 "employment type, the quick-apply count with the first quick-apply listing's pay, and how "
 "many distinct cities the unfiltered Atlanta results cover (list them). PASS requires every "
 "value and the full city list exactly as shown. FAIL on a wrong page count, wrong listing or "
 "an incomplete city list.",
"ZipRecruiter--6":
 "FACT CHECKPOINTS: Search warehouse jobs in Dallas, TX, apply the quick-apply-only filter, "
 "open the first quick-apply listing, open its company profile, return to the filtered search, "
 "open the second listing, clear the quick-apply filter and apply the within-5-days date "
 "filter. Report the base count, the quick-apply count, the first listing's title, company, "
 "city, hourly pay, posted age and employment type, the company's open-job count, the second "
 "listing's pay range and city, and the within-5-days count with the first job's posted age. "
 "PASS requires every value exactly as shown. FAIL on any wrong count or wrong listing.",
"ZipRecruiter--7":
 "FACT CHECKPOINTS: Search software engineer jobs in San Francisco, CA, open the FIRST "
 "result, open its company profile, open the company's San Francisco jobs page, search again "
 "with the within-5-days date filter and open the first result. Report the listing's title, "
 "company, location and location type, employment type, posted age and every badge shown, "
 "the company's industry and size, the first platform the description says the role tunes, "
 "the company's headquarters, website and open-job count, its San Francisco jobs-page count, "
 "the within-5-days count, and the first result's posted age and quick-apply status. PASS "
 "requires every value exactly as the opened pages show them. FAIL on any wrong badge, wrong "
 "count or invented platform.",
"ZipRecruiter--8":
 "FACT CHECKPOINTS: Search registered nurse jobs in New York, NY, open the first result, open "
 "its company profile, open the company's New York jobs page, search again with the "
 "quick-apply filter and open the first result, clear the filters, open the second result and "
 "open its company profile. Report the first listing's title, company, city, hourly pay, "
 "employment type and posted age, the company's open-job count and New York jobs-page count, "
 "the quick-apply count with the first result's company and pay, the second listing's title, "
 "city and pay, and its company's Breakroom rating score with the response count. PASS "
 "requires every value exactly as shown. FAIL on any wrong count or wrong company.",
"ZipRecruiter--9":
 "FACT CHECKPOINTS: Search software engineer jobs in San Francisco, CA, open the first "
 "result, open its company profile, search again applying the Remote filter then the "
 "within-5-days filter, open Browse, the letter S and the Software Engineer title page, open "
 "the salary page, and open the first nearby job. Report the base count, the first listing's "
 "location type, employment type and posted age, the company's industry and headquarters, "
 "the Remote count, the within-5-days count, the title page's open roles and average pay, the "
 "salary page's average yearly and hourly pay and 25th percentile, and the first nearby "
 "job's title and company. PASS requires every value exactly as the opened pages show them. "
 "FAIL on any wrong count, wrong percentile or wrong company.",
"ZipRecruiter--10":
 "FACT CHECKPOINTS: Open Browse from the home page, the letter R and the Registered Nurse "
 "title page, open the salary page, open the first nearby job, open that company's profile, "
 "and finally search registered nurse jobs in New York, NY with the quick-apply filter, "
 "opening the first result. Report the title page's open roles and average pay, the salary "
 "page's average yearly and hourly pay and median, the first nearby job's title, company, "
 "location type and pay, the company's industry as its profile shows it (state clearly if the "
 "page shows none), the top three paying cities with averages, the best-paying related title "
 "with its average, the New York count, the quick-apply count, and the first quick-apply "
 "result's company and hourly pay. PASS requires every value exactly as shown. FAIL on wrong "
 "percentiles, wrong cities or invented industry values.",
"ZipRecruiter--11":
 "FACT CHECKPOINTS: Open the Software Engineer salary page from Browse, open its San Francisco "
 "version, search software engineer jobs nationwide, apply the senior experience filter, add "
 "the Remote filter, and open the first remaining senior listing. Report the national average "
 "yearly and hourly pay, median, 10th and 90th percentiles, the San Francisco average yearly "
 "and hourly pay, median and 25th percentile, the nationwide job count, the senior count, "
 "the senior-plus-remote count, the first senior listing's title, company, pay and posted "
 "age, and the first two top-paying cities the national page lists with their averages. PASS "
 "requires every value exactly as the opened pages show them. FAIL on any wrong percentile "
 "or wrong count.",
"ZipRecruiter--12":
 "FACT CHECKPOINTS: Open the Accountant salary page from Browse, search accountant jobs in "
 "Denver, CO with a $70,000 minimum-salary filter, open the first remaining listing, clear "
 "the salary filter, apply the within-10-days date filter, add the quick-apply filter, and "
 "open the Denver accountant salary page. Report the national average yearly and hourly pay, "
 "median and 75th percentile, how many histogram bands hold 15% of jobs or more, the Denver "
 "base count, the $70,000-filtered count, the first listing's title, company and pay, its "
 "posted age and employment type, the within-10-days count, the quick-apply count, and the "
 "Denver salary page's average and 25th percentile. PASS requires every value exactly as "
 "shown. FAIL on any wrong count or wrong percentile.",
"ZipRecruiter--13":
 "FACT CHECKPOINTS: Open the career-advice blog from the footer's Blog link, open the Trends "
 "category, open the article about top industry insights to fuel your job search, report one "
 "more Trends article, open the Tips & Advice category, and finally search data analyst jobs "
 "in Seattle, WA applying the within-5-days filter and opening the first result. Report how "
 "many categories the blog page lists, how many articles Trends holds, the article's author "
 "and publish date, its four numbered insight headings, the hottest trend it names, the other "
 "Trends article with author and publish date, the Tips & Advice article count, the data "
 "analyst count, the within-5-days count, and the first result's company and pay. PASS "
 "requires every value exactly as the opened pages show them. FAIL on any wrong count, wrong "
 "author or wrong date.",
"ZipRecruiter--14":
 "FACT CHECKPOINTS: Open the Veterans category from the blog home, open the article about job "
 "search tips for military veterans, open the other veterans-category article, locate the "
 "hot-weather interview-dressing article's category on the blog home, and finally search "
 "electrician jobs in Houston, TX applying the within-5-days then the quick-apply filter and "
 "opening the first listing. Report the veterans article count, the first article's author, "
 "publish date and updated date with its tips as titles only, the other article's title, "
 "author and publish date, the hot-weather article's category, author and publish date, the "
 "electrician count, the within-5-days count, the quick-apply count, and the first listing's "
 "company, pay and posted age. PASS requires every value exactly as shown. FAIL on any wrong "
 "date, wrong author or wrong count.",
"ZipRecruiter--15":
 "FACT CHECKPOINTS: Create a free job-seeker account (name, your own email, an 8+ character "
 "password, location Dallas, TX), search warehouse jobs in Dallas, TX, apply the "
 "quick-apply-only filter, 1-Click Apply to the first listing, and open My Applications. "
 "Report the confirmation heading, the job title and company the confirmation shows, the "
 "application status, the job shown in My Applications with its current status and the "
 "single timeline entry with its note, and how many saved jobs the account starts with. PASS "
 "requires the account to be created in the environment and every value exactly as shown. "
 "FAIL if no application row exists or any reported value is wrong.",
"ZipRecruiter--16":
 "FACT CHECKPOINTS: Log in as alice.j@test.com, open My Profile, open Saved Jobs, unsave the "
 "Manhattan listing at the urology employer (the task's gastroenterology descriptor matches "
 "no saved listing — report that honestly), and create a new daily job alert for licensed "
 "practical nurse in Brooklyn, NY. Report the profile's headline, years of experience and "
 "location, every saved job's title, company, city and pay, which two jobs remain with their "
 "cities, and the full alerts table afterwards: every alert's search, location and frequency. "
 "PASS requires the unsave and the alert to persist in the environment and every value "
 "exactly as shown. FAIL if the saved-job count or alerts table is wrong.",
"ZipRecruiter--17":
 "FACT CHECKPOINTS: Log in as bob.c@test.com, open My Applications, open that job's page, "
 "open the resume page, open Saved Jobs and unsave the first, open Job Alerts and create a "
 "weekly data engineer alert for Seattle, WA. Report the application's title, company and "
 "city, the applied date, the current status and every timeline entry with dates and notes, "
 "the job's pay, location type and posted age, the resume's title, completeness label, "
 "summary, experience employer and dates, and every skill with its years, what remains in "
 "Saved Jobs, and the full alerts table. PASS requires the unsave and the new alert to "
 "persist and every value exactly as shown. FAIL on any wrong timeline entry or wrong table.",
"ZipRecruiter--18":
 "FACT CHECKPOINTS: Log in as dana.k@test.com, open the resume page, edit the resume to add "
 "QuickBooks as a new skill with 2 years and save, open My Applications, and open Job Alerts. "
 "Report the resume's title, summary, both experience entries with employers and dates, both "
 "education entries, every skill with its years, the new total skill count and the updated-at "
 "date after saving, the application's title, company, city, current status and every timeline "
 "entry with dates, and every alert's search, location and frequency. PASS requires the "
 "QuickBooks skill edit to persist in the environment and every value exactly as shown. FAIL "
 "if the skill edit is missing or any reported value is wrong.",
"ZipRecruiter--19":
 "FACT CHECKPOINTS: Search teacher jobs in Chicago, IL, open the first listing and its "
 "company profile, search receptionist jobs in Los Angeles, CA with the within-5-days filter, "
 "open Browse, the letter R and the first title's salary page. Report the teacher count, the "
 "first listing's title, company, posted age, employment type and pay if shown, the company's "
 "industry and open-job count, the receptionist count, the within-5-days count, the first "
 "receptionist listing's title, company and pay, the first two job titles on the letter-R page "
 "and how many titles that page holds, and the first title's salary-page average yearly pay. "
 "PASS requires every value exactly as the opened pages show them. FAIL on any wrong count or "
 "wrong title.",
}


def main():
    lines = TASKS.read_text(encoding="utf-8").splitlines()
    out = []
    appended = 0
    for line in lines:
        if not line.strip():
            continue
        row = json.loads(line)
        tid = row["id"]
        if "verifier_path" in row or "judge_rubric" in row:
            out.append(line)
            continue
        rubric = RUBRICS[tid]
        prefix = line.rstrip()
        assert not re.search(r'"answer"\s*:', prefix), "tasks.jsonl must never carry an answer key"
        new_row = prefix[:-1] + ', "verifier_path": "sites/ziprecruiter/verify/verify_%d.py", "judge_rubric": %s}' % (
            int(tid.split("--")[1]), json.dumps(rubric))
        json.loads(new_row)  # sanity
        assert new_row.startswith(prefix[: prefix.rindex(", ")])
        # byte-identical contributor prefix: the original line + appended keys
        out.append(new_row)
        appended += 1
    TASKS.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"appended verifier_path + judge_rubric to {appended} rows (idempotent)")


if __name__ == "__main__":
    main()
