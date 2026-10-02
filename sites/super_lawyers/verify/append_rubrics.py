#!/usr/bin/env python3
"""Merge verifier_path + judge_rubric into sites/super_lawyers/tasks.jsonl.

The contributor's 5-key rows (web_name, id, ques, web, upstream_url) are kept
BYTE-FOR-BYTE: each output line is the original line with its closing brace
replaced by the two appended reviewer keys. There is no `answer` key — ground
truth lives only in the verifiers.
"""
from __future__ import annotations

import json
from pathlib import Path

RUBRICS = {
    "Super Lawyers--0":
        "Verify the agent opened the Seattle personal injury results page, identified "
        "Lara Herrmann as the selectee first admitted in 2000 who handles aviation "
        "cases, and opened her profile. The answer must state she attended Seattle "
        "University School of Law and that Law Dragon magazine named her one of the "
        "top 500 consumer lawyers, and confirm an inquiry about the rear-end collision "
        "was sent from alice.j@test.com's account and appears in her inquiry history. "
        "Fail answers naming a different attorney, a different law school, or a "
        "different honor.",
    "Super Lawyers--1":
        "Verify the agent browsed the attorney directory, opened the Criminal "
        "Defense category, and reached its Seattle results page. The answer must "
        "report 27 rated attorneys listed, the first attorney card Chris Black with "
        "phone 206-737-9807, and from his profile the University of Washington "
        "School of Law and first-admitted 2001, and confirm a guest inquiry from "
        "dui.help@example.com was submitted via the profile contact form. Fail "
        "answers with a different count, attorney, phone, school, or year, or "
        "without the inquiry.",
    "Super Lawyers--2":
        "Verify the agent opened the Dallas estate planning results page, identified "
        "Tresi Moore Weeks as the attorney first admitted in 1987, and opened her "
        "profile. The answer must state her law school (Baylor University School of "
        "Law) and every focus area her profile lists (Living Wills, Power of Attorney, "
        "Probate & Estate Administration, Trusts, Wills), and confirm a guest inquiry "
        "from aunt.help@example.com about a living trust was submitted. Fail answers "
        "naming a different attorney, year, or school, or missing focus areas.",
    "Super Lawyers--3":
        "Verify the agent opened the Clifford Law Offices firm profile and every "
        "attorney profile it lists. The answer must state the firm lists 6 attorneys, "
        "give its office address (120 North LaSalle Street, 36th Floor, Chicago, IL "
        "60602), name Robert A. Clifford as the partner first admitted in 1976 with "
        "the National Law Journal Lifetime Achievement honor, name Bradley M. "
        "Cosgrove as the most recently admitted partner (2006), and report that 2 "
        "attorneys were first admitted in the 1980s. Fail answers with a different "
        "count, address, partners, or honor.",
    "Super Lawyers--4":
        "Verify the agent opened the 2026 Washington Top 10 list and the 2026 Women "
        "Washington Top 50 list. The answer must name exactly the four attorneys on "
        "both lists (Sherri M. Anderson, Lora L. Brown, Karolyn Hicks, Lisa A. Sharpe), "
        "name Todd W. Gardner as the Top 10 selectee whose office city is Renton, and "
        "report his profile phone number (425-226-7920). Fail answers naming a "
        "different intersection set, a different Renton selectee, or a wrong phone.",
    "Super Lawyers--5":
        "Verify the agent opened Florida's top lists, the Miami-specific Top 100 "
        "list, Heather L. Apicella's profile, the Florida-wide Top 100 list, and the "
        "women's list. The answer must state Florida publishes 2 Top 100 lists, give "
        "the women's list title (Top 50: 2026 Women Florida Super Lawyers), name "
        "Heather L. Apicella as the first Miami Top 100 attorney with her primary "
        "practice area (Family Law), office city (Boca Raton), and phone "
        "(561-928-3963), name the first attorney on the Florida-wide Top 100 "
        "(Jeffrey A. Baskies) and on the women's list (Amy B. Beller), and state "
        "Heather appears on neither of those lists. Fail answers with wrong counts, "
        "titles, attorneys, or phone.",
    "Super Lawyers--6":
        "Verify the agent logged in as bob.c@test.com and opened the saved attorneys "
        "page. The answer must confirm the attorneys with offices in Tacoma (Thomas "
        "B. Vertetis) and Bellevue (Sherri M. Anderson) were removed, report that 2 "
        "saved attorneys remain (Todd W. Gardner and Lora L. Brown), and confirm the "
        "agent opened the Renton attorney Todd W. Gardner's profile (phone "
        "425-226-7920) and sent him an inquiry about the rear-end collision case from "
        "bob's account. Fail answers removing different attorneys, misreporting the "
        "remaining set or phone, or without the inquiry.",
    "Super Lawyers--7":
        "Verify the agent logged in as david.k@test.com, created saved searches for "
        "personal injury attorneys in Miami and family law attorneys in Chicago, and "
        "removed the DUI-DWI in Denver saved search. The answer must report 3 saved "
        "searches remain and list their labels exactly as shown: 'Personal Injury in "
        "Miami, Florida', 'Family Law in Chicago, Illinois', and 'Employment & Labor "
        "in Boston', and report how many attorney cards the Miami personal injury "
        "results page lists (31). Fail answers with wrong labels, counts, or card "
        "count.",
    "Super Lawyers--8":
        "Verify the agent logged in as alice.j@test.com and opened her inquiry "
        "history. The answer must name Matthew D. Dubin as the most recently contacted "
        "attorney, state he practices in Seattle, and confirm a follow-up inquiry "
        "asking how long a settlement typically takes was sent and appears in the "
        "inquiry history. Fail answers naming a different attorney or city, or "
        "without the follow-up.",
    "Super Lawyers--9":
        "Verify the agent logged in as carol.d@test.com, changed the display name to "
        "Carol D. Davis and the email to carol.d.davis@example.com, logged out, and "
        "logged back in with the new email. The answer must confirm both changes took "
        "effect and report 3 saved attorneys with their practice cities (Steven W. "
        "Fogg — Seattle, Richard Friedman — Bremerton, Karolyn Hicks — Seattle). Fail "
        "answers that do not confirm the new credentials or misreport the saved set.",
    "Super Lawyers--10":
        "Verify the agent registered maria_l with maria.lopez@example.com, found "
        "Sherri M. Anderson through the 2026 Washington Top 10 list, saved her to the "
        "new account, and sent her a child-custody inquiry from the profile contact "
        "form. The answer must report the site's confirmation ('Your inquiry has been "
        "sent. Track it under My inquiries.'). Fail answers saving or contacting a "
        "different attorney or without the confirmation.",
    "Super Lawyers--11":
        "Verify the agent read the elderly financial abuse article in the legal "
        "article resources and the Florida elder-financial-abuse Ask a Lawyer "
        "question. The answer must list two warning signs the article actually names "
        "(e.g. large withdrawals from bank accounts or sudden changes in spending "
        "habits; someone the older person recently met making financial decisions) "
        "and report the answering attorney Natasha Perez, her city (Miami, FL), and "
        "phone (305-998-0051). Fail answers with warning signs the article does not "
        "list or a different attorney.",
    "Super Lawyers--12":
        "Verify the agent searched the Ask a Lawyer section for severance questions "
        "and opened the Minnesota question, then searched for overtime questions and "
        "opened the New York one. The answer must name Beth E. Bertelson (Minneapolis, "
        "MN, phone 612-278-9832), summarize what the answer recommends before "
        "signing, report it was last answered April 8, 2026, name the New York "
        "answering attorney Joseph A. Fitapelli with last-answered October 11, 2024, "
        "and state which was answered more recently (the Minnesota one). Fail answers "
        "with different attorneys, dates, or comparison.",
    "Super Lawyers--13":
        "Verify the agent browsed the Ask a Lawyer answers by legal topic (criminal "
        "defense) and opened all three state questions. The answer must name the "
        "three states (Kansas, New Jersey, Pennsylvania), the Kansas answering "
        "attorney Paul D. Cramm (Overland Park, KS) with one piece of advice the "
        "answer gives, the New Jersey answering attorney Peter G. Aziz (Clifton, NJ, "
        "phone 973-435-2245), and the Pennsylvania answering attorney Evan Kelly "
        "(West Chester, PA) with the date that question was last answered "
        "(September 28, 2022). Fail answers with wrong states, attorneys, phones, "
        "or dates.",
    "Super Lawyers--14":
        "Verify the agent opened the April Jones feature article (Finding the After) "
        "and the related article Bump in the Road. The answer must state the article "
        "was published in 2026 Colorado Super Lawyers magazine by Amy White on "
        "March 19, 2026, list the three wish-list things (cat, condo, convertible), "
        "state she led the Sam Cary Bar Association as president twice, becomes "
        "president of the Colorado Bar Association in 2027, founded Denver's Jones "
        "Law Firm, identify April D. Jones as the featured lawyer with her office "
        "city (Greenwood Village, CO), and report the question Bump in the Road's "
        "subtitle asks (pothole liability) and an attorney it features. Fail answers "
        "with different facts.",
    "Super Lawyers--15":
        "Verify the agent opened the first five Houston immigration attorneys' "
        "profiles. The answer must identify Beatriz Trillos Ballerini as the one who "
        "also speaks Italian, state her law school (South Texas College of Law "
        "Houston), her exact Super Lawyers selection years (2021 - 2026), and that 3 "
        "of the five speak Spanish. Fail answers naming a different Italian speaker, "
        "law school, years, or Spanish count.",
    "Super Lawyers--16":
        "Verify the agent opened the Seattle criminal defense results page and the "
        "profile of the attorney whose practice-area chart shows 70 percent criminal "
        "defense while concentrating on DUI and white-collar work (Court Will). The "
        "answer must give the three chart areas with exact percentages (70% Criminal "
        "Defense, 20% Criminal Defense: DUI/DWI, 10% Criminal Defense: White "
        "Collar), his first-admitted year (2003, California), and office phone "
        "(206-209-5585). Fail answers about a different attorney or wrong chart "
        "values.",
    "Super Lawyers--17":
        "Verify the agent opened the Chicago family law attorneys results page "
        "(/attorneys/family-law/illinois/chicago/) and the first attorney's profile. "
        "The answer must list the court locations shown (the Circuit Court of Cook "
        "County - County Division, - Criminal Division, and - First Municipal "
        "District), give the First Municipal District's phone ((312) 603-6132) and "
        "the Criminal Division's ((773) 674-3160), report 35 attorneys listed and "
        "the first one's name, firm, and phone (Mary Davis, Law Office of Mary "
        "Davis, P.C., 630-748-8819), and from her profile DePaul University College "
        "of Law and first-admitted 1991. Fail answers from a different page or with "
        "wrong details.",
    "Super Lawyers--18":
        "Verify the agent opened the Denver DUI attorneys results page, the related "
        "Car Accident page for Denver, and the DUI page for one of the nearby cities. "
        "The answer must report the DUI page's title (Top Rated DUI-DWI Lawyers in "
        "Denver, CO), the nearby cities (Englewood, Greenwood Village, Castle Rock, "
        "Broomfield, Centennial), the related practice areas (Car Accident, Criminal "
        "Defense, Drug & Alcohol Violations, Trucking Accidents), the first attorney "
        "card's name and phone (Heidi Tripp, 983-224-0853), and that no Denver "
        "attorneys are listed on the Car Accident page nor on the nearby-city DUI "
        "page. Fail answers with wrong cities, areas, title, or claiming attorneys "
        "are listed.",
    "Super Lawyers--19":
        "Verify the agent opened both Anne Bremner's and Kevin Coluccio's profiles "
        "from the Seattle personal injury results page. The answer must state Kevin "
        "Coluccio has more total Super Lawyers selection years (28, 1999-2026) than "
        "Anne Bremner (27), give each first-admitted year (Bremner 1983, Coluccio "
        "1986), each law school (both Seattle University School of Law), each tagline "
        "practice area (Bremner Civil Litigation, Coluccio Personal Injury), that "
        "Anne Bremner appears first on the results page, and Coluccio's phone "
        "(206-826-8200). Fail answers reversing the comparison or with wrong years, "
        "schools, taglines, or phone.",
}


def main():
    tasks = Path(__file__).resolve().parents[1] / "tasks.jsonl"
    original = tasks.read_text(encoding="utf-8").splitlines()
    assert len(original) == 20, len(original)
    out_lines = []
    for line in original:
        row = json.loads(line)
        tid = row["id"]
        assert tid in RUBRICS, tid
        assert sorted(row.keys()) == ["id", "ques", "upstream_url", "web",
                                      "web_name"], f"{tid}: unexpected keys {sorted(row.keys())}"
        n = int(tid.split("--")[1])
        suffix = (', "verifier_path": ' +
                  json.dumps(f"sites/super_lawyers/verify/verify_{n}.py") +
                  ', "judge_rubric": ' + json.dumps(RUBRICS[tid]) + "}")
        assert line.endswith("}"), line[-20:]
        out_lines.append(line[:-1] + suffix)
    tasks.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"[merge] {len(out_lines)} rows written to {tasks}")


if __name__ == "__main__":
    main()
