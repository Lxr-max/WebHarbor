#!/usr/bin/env python3
"""Write sites/super_lawyers/tasks.jsonl (contributor phase: 5 keys per row)."""
import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent / "tasks.jsonl"

WEB_NAME = "Super Lawyers"
WEB = "http://localhost:40098/"
UPSTREAM = "https://superlawyers.com/"

TASKS = [
    # --- search → SERP → profile → verify → act -----------------------------
    "I was rear-ended on I-5 and need a top-rated Seattle personal injury attorney. On the Seattle personal injury results page, find the selectee who was first admitted in 2000 and also handles aviation cases. Open their profile and report their law school and the honor Law Dragon magazine gave them. Then log in as alice.j@test.com (password TestPass123!) and send that attorney an inquiry about the rear-end collision, using the contact form on their profile.",
    "I got a DUI ticket in Seattle. Browse the attorney directory by practice area, open the Criminal Defense category, and go to its Seattle results page. Report how many rated attorneys are listed there, the name of the first attorney card, and the phone number that card shows. Then open that first attorney's profile and report the law school they attended and the year they were first admitted to practice. Finally, use the contact form on their profile to send them an inquiry as a guest, with your email dui.help@example.com, about your DUI case.",
    "My aunt in Dallas needs an estate planning attorney and insists on someone admitted to the Texas bar in the 1980s. From the Texas directory page navigate to Dallas, open the estate planning results, and identify the attorney first admitted in 1987. Report their name and law school, plus every focus area their profile lists. Finally, use the contact form on their profile to send them an inquiry as a guest with your email aunt.help@example.com asking about a living trust.",
    "A colleague recommended Clifford Law Offices in Chicago for a serious injury case. Find the firm's profile page and report how many attorneys it lists. Open each attorney's profile and report the name of the partner first admitted in 1976, the lifetime honor The National Law Journal gave them, and the name of the partner admitted most recently with the year they were admitted. Also report how many of the firm's attorneys were first admitted in the 1980s, and the firm's office address as shown on its profile.",
    # --- top lists ------------------------------------------------------------
    "Compare Super Lawyers' 2026 Washington Top 10 list with the 2026 Women Washington Top 50 list. Report the names of the four attorneys who appear on the Top 10 list and also on the Women's list, and name the Top 10 selectee whose office city is Renton. For that Renton attorney, open their profile and report their phone number.",
    "From the Top Lists hub, open Florida's lists. Report how many Top 100 lists Florida publishes, the title of its women's list, and the name of the first attorney on the Miami-specific Top 100 list. Then open that first Miami attorney's profile and report their primary practice area, office city, and phone number. Finally, open the Florida-wide Top 100 list and the women's list, and report the name of the first attorney on each and whether the first Miami attorney appears on either list.",
    # --- account: favorites / saved searches / inquiries ----------------------
    "Log in as bob.c@test.com (password TestPass123!). I've decided to work with the attorney from Renton, so remove the saved attorneys whose offices are in Tacoma and Bellevue from my saved attorneys list, keeping the others. Report how many saved attorneys remain and the names of the ones you kept. Then open the Renton attorney's profile, report their phone number, and use the contact form there to send them an inquiry about my rear-end collision case.",
    "Log in as david.k@test.com (password TestPass123!). Create a saved search for personal injury attorneys in Miami and another for family law attorneys in Chicago, then remove my saved search for DUI attorneys in Denver. Report how many saved searches remain on the account and list their labels exactly as shown. Finally, open the Miami personal injury results page and report how many attorney cards it lists.",
    "Log in as alice.j@test.com (password TestPass123!) and open my contact inquiries. Report the name of the attorney I most recently contacted and the city they practice in. Then send that same attorney a follow-up inquiry asking how long a settlement typically takes, and confirm the inquiry appears in my inquiry history.",
    "Log in as carol.d@test.com (password TestPass123!). Change my display name to Carol D. Davis and my email to carol.d.davis@example.com. Log out, then log back in with the new email and confirm both changes took effect. Finally report how many saved attorneys are in my account and the practice city of each.",
    "Create a new account with the username maria_l, email maria.lopez@example.com, and a password of your choice (at least 8 characters). Then find the attorney Sherri M. Anderson through the 2026 Washington Top 10 list, save her to your saved attorneys, and send her an inquiry about a child custody case using the contact form on her profile. Report the confirmation the site shows.",
    # --- resources / answers cross-chains --------------------------------------
    "My mother in Miami may be a victim of financial exploitation by a caregiver. Find the legal article resources section, read the article about elderly financial abuse, and report two warning signs it lists. Then find the Ask a Lawyer question about suing for elder financial abuse in Florida, and report the answering attorney's name, their city, and the phone number shown to contact them.",
    "In Minnesota I was offered a severance package I'm not sure I should sign. Search the Ask a Lawyer section for severance questions, open the Minnesota question, and report the answering attorney's name, their city, the phone number shown, one sentence on what the answer recommends doing before signing, and the date it was last answered. Then search for overtime questions, open the New York one, and report its answering attorney's name and the date it was last answered. Which question was answered more recently?",
    "On the Ask a Lawyer hub, browse answers by state and by legal topic. Report which three states have criminal defense questions answered. Open each state's question and report the answering attorney's name and city for each, plus the phone number shown on the New Jersey page and the date the Pennsylvania question was last answered. For the Kansas question, also report one specific piece of advice the answer gives.",
    # --- feature articles -------------------------------------------------------
    "Read the attorney feature article about April Jones, the Denver family lawyer who bought her firm's building. Report the article's publication date, author, and magazine; the three things on the wish list she describes; which bar association she led twice as president; the leadership role she takes on in 2027; and the firm she founded. Also report which featured lawyer appears with a photo on the article page and their office city. Then open the related article 'Bump in the Road' and report the question its subtitle asks and the attorney it features.",
    # --- deep profile hunting -----------------------------------------------------
    "I need an immigration attorney in Houston who can speak with my Italian relatives in Italian. Compare the languages spoken by the first five immigration attorneys on the Houston results page by opening each profile. Report which one also speaks Italian, the law school they attended, the exact years they have been selected to the Super Lawyers list, and how many of the five speak Spanish.",
    "I'm facing a white-collar charge and want a Seattle criminal defense attorney who concentrates on DUI and white-collar work. On the Seattle criminal defense results page, find the attorney whose practice-area chart shows 70 percent criminal defense. Report the three practice areas in their chart with their exact percentages, the year they were first admitted, and their office phone number.",
    # --- SERP rails / courts -------------------------------------------------------
    "I'm filing for divorce in Chicago and want to know where to file. From the Chicago family law attorneys results page, report the names of the court locations listed, the phone number of the Circuit Court of Cook County's First Municipal District, and the phone number of its Criminal Division. Also report how many attorneys are listed on that results page and the name, firm, and phone number of the first one. Then open the first attorney's profile and report their law school and the year they were first admitted to practice.",
    "I need a DUI attorney near Denver but I'm flexible on the exact city. From the Denver DUI attorneys results page, report the title it shows, the nearby cities Super Lawyers suggests, the related practice areas listed, and the name and phone number of the first attorney card. Then open the related Car Accident page for Denver, report whether any Denver attorneys are listed on it. Finally, open the DUI page for one of the nearby cities and report whether any attorneys are listed there.",
    # --- comparison ---------------------------------------------------------------
    "Two well-known Seattle personal injury attorneys, Anne Bremner and Kevin Coluccio, were both recommended to me. Open both of their profiles and report which one has more total years of Super Lawyers selections, the year each was first admitted to practice, the law school each attended, and the practice area each one's tagline names. Also report which of the two appears first on the Seattle results page and the phone number of the one with more selection years.",
]

rows = []
for i, ques in enumerate(TASKS):
    rows.append({
        "web_name": WEB_NAME,
        "id": f"Super Lawyers--{i}",
        "ques": ques,
        "web": WEB,
        "upstream_url": UPSTREAM,
    })

with OUT.open("w", encoding="utf-8") as fh:
    for row in rows:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
print(f"wrote {len(rows)} tasks to {OUT}")
for row in rows:
    assert len(row["ques"].split()) <= 100, (row["id"], len(row["ques"].split()))
print("all task word counts <= 100 words")
