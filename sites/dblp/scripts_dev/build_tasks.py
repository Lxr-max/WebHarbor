#!/usr/bin/env python3
"""Emit sites/dblp/tasks.jsonl (5-key rows) and validate the format.

Task design rules (reviewer contract):
- 5 keys: web_name, id, ques, web, upstream_url (verifier slots are
  appended later by the reviewer contract)
- goal-style prompts, <=100 words each, no mechanical click-by-click
  instructions, no answer leakage, no direct URLs to answers
- every task honestly requires >=15 atomic actions on the mirror
  (page navigations, form-field fills, form submits, facet/filter clicks,
  pagination, downloads; reading values is free)
- functional domains stay diverse: search semantics, author profiles,
  venue/edition browsing, records + BibTeX, watchlists, saved searches,
  saved papers + export, search history, profile editing, registration.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
OUT = os.path.join(SITE, 'tasks.jsonl')

WEB = "http://localhost:40115/"
UPSTREAM = "https://dblp.org/"
NAME = "dblp"

TASKS = [
    # 0 — publication search semantics marathon
    "From the home page search publications for graph neural network; report the "
    "count. Refine by the newest year facet (report count and first title), then "
    "clear it. Open results page two; report the first hit's title and venue. "
    "Open that record (report type and mdate), download its BibTeX entry type, "
    "then open its venue and newest edition, reporting the edition title and "
    "first record's title. Rerun as an exact-word query for graph; report the "
    "count. Open the first hit's first author (report record count and busiest "
    "year), their newest publication's title, that venue's record count, and its "
    "newest edition's records.",
    # 1 — author chain: homonyms, coauthors, citation walk
    "From the home page author-search Jiawei Han; report how many profiles match. "
    "Open the University of Illinois professor's profile (report full dblp name, "
    "affiliation, award). Open the other person sharing the name; report their "
    "record count. Return, open his top coauthor (report name and joint count), "
    "then that coauthor's top coauthor (report name and joint count). Return, "
    "open his newest publication (report title and venue), that venue's record "
    "count and newest edition's record count, the edition's first record's title, "
    "that record's first author's record count, their top coauthor's name, and "
    "that coauthor's newest publication's title and venue.",
    # 2 — combined search sections + venue chain
    "From the home page run a combined dblp search for sigmod; report the author, "
    "venue and publication counts. Open the author section's first author (report "
    "record count, newest publication's title and venue). Search venues for "
    "sigmod, open the ACM SIGMOD Conference page (report note line, record count, "
    "busiest year, top frequent author), the newest edition (report title, "
    "editors, records), its first record (report DOI), download its BibTeX entry "
    "type, then open its first author, their top coauthor, that coauthor's newest "
    "publication, and its venue's record count and newest edition's records.",
    # 3 — conference browse + NeurIPS deep chain
    "From the home page browse the conference list; report how many venues it "
    "carries. Open the Conference on Neural Information Processing Systems venue "
    "(report record count, busiest year, top two frequent authors). Open the "
    "newest edition; report title, records. Open its first paper (title, authors, "
    "venue), download its BibTeX key. Open the first author's profile (report "
    "record count, busiest year), their top coauthor, that coauthor's newest "
    "publication, that venue's newest edition, the edition's first record, that "
    "record's first author, and their top coauthor's name. Search publications "
    "for attention in this venue; report the count and first title.",
    # 4 — journal browse + PVLDB volume chain
    "From the home page browse the journal list; report how many venues it "
    "carries. Open Proceedings of the VLDB Endowment (report volume count, record "
    "count, top frequent author), the newest volume (report title, year, "
    "records), its first record (report title, pages, DOI) and second record "
    "(report title and author count). From it open the first author's profile "
    "(report record count, busiest year), their top coauthor, that coauthor's "
    "newest publication, its venue's record count and newest edition's records, "
    "the edition's first record's title, that record's first author, their top "
    "coauthor, and that coauthor's newest publication's title and venue.",
    # 5 — venue search + TODS/TOIS comparison
    "From the home page search venues for transactions; report the matches and "
    "each venue's record count. Open the ACM Transactions on Database Systems "
    "page (report ISO abbreviation, volumes, busiest year), the newest volume "
    "(report title and records), its first record (report title and pages), that "
    "record's first author and their top coauthor (report counts and joint "
    "count). Return to the venue search, open the Transactions on Information "
    "Systems venue (report record and volume counts), its newest volume's title, "
    "its first record's title and DOI, that record's first author, their top "
    "coauthor, the coauthor's newest publication, and its venue's record count.",
    # 6 — record details + BibTeX + author chain
    "From the home page search publications for query optimization; report the "
    "count. Refine by the oldest year facet (report count, first hit's title and "
    "venue). Open that record (report DOI, pages, mdate); report the BibTeX key "
    "shown, download the .bib file and report the entry type and its journal or "
    "booktitle field. Open the first author's profile (report record count and "
    "busiest year), their top coauthor (report name and joint count), the "
    "coauthor's newest publication (report title and venue), and that venue's "
    "record count and newest edition's record count.",
    # 7 — search operators: OR, exact word, type and year refine
    "From the home page search publications for graph|network; report the count. "
    "Rerun as an exact-word query for network; report the count. Refine the first "
    "search by the conference-paper type; report the count, clear it, refine by "
    "the newest year; report the count. Open the first hit (report title, venue, "
    "year), then its record (report DOI and mdate). Open the record's venue "
    "(report edition count), its newest edition (report record count), that "
    "edition's first record (report title and first author), and that author's "
    "record count.",
    # 8 — registration + save + export + persistence
    "Register a new dblp account with your own name and a fresh email (password "
    "at least 8 characters). Search publications for side channel; report the "
    "count. Open the first hit's record and save it to a new collection named "
    "Security reading with the note first pick. Open the second hit and save it "
    "to the same collection. Open saved papers; report both titles and the "
    "collection name. Export the collection as BibTeX; report the entry count and "
    "first entry type. Log out, log back in, report the collection remains, "
    "remove one record and report what is left.",
    # 9 — login + author watchlist management
    "Log in as alice.j@test.com (password TestPass123!). Open the watchlist; "
    "report every watched author's name and record count and every watched venue "
    "with its record count. Author-search Jiawei Han, open the University of "
    "Illinois professor's profile and add him to the watchlist. Reopen the "
    "watchlist; report the new author total. Remove one previously watched "
    "author; report who remains. Open the watched NeurIPS venue (report record "
    "count and busiest year) and its newest edition (report record count), remove "
    "the venue from the watchlist and report the remaining venue names.",
    # 10 — login + venue watching + TMLR chain
    "Log in as bob.c@test.com (password TestPass123!). Open the watchlist; report "
    "every watched venue with its record count. From the home page search venues "
    "for learning, open the Transactions on Machine Learning Research page "
    "(report record count, volume count, top frequent author). Add it to the "
    "watchlist; reopen the watchlist and report its entry. Open the newest volume "
    "(report title and record count), its first record (report title and DOI), "
    "and that record's first author (report record count). Log out; report where "
    "the watchlist page sends you.",
    # 11 — login + saved searches lifecycle
    "Log in as dana.k@test.com (password TestPass123!). Open saved searches; "
    "report every query with its search kind. Run the question answering search; "
    "report the count. From the home page search publications for language model, "
    "save that search, and report the full table. Delete the question answering "
    "search; report which searches remain. Run the remaining search via its run "
    "link; report the count, open the first hit's record (report DOI), and save "
    "that record to your library, reporting the collection it lands in.",
    # 12 — login + saved papers collections + exports
    "Log in as carol.d@test.com (password TestPass123!). Open saved papers; "
    "report every collection with its record count and each record's title. "
    "Search publications for fuzzing; report the count. Open the first hit's "
    "record and save it to a new collection named Audit queue with the note must "
    "read. Open the second hit and save it there too. Export My Library as "
    "BibTeX; report its entry count, then export Audit queue; report its count. "
    "Remove one Audit queue record; report what remains. Open the watchlist; "
    "report the watched venues.",
    # 13 — login + search history lifecycle
    "Log in as dana.k@test.com (password TestPass123!). Open search history; "
    "report every query with its hit count. From the home page run three "
    "publication searches of your choice; report each count. Reopen history; "
    "report the three new entries and the total count. Clear the history; report "
    "what the page shows. Author-search Zhang; report how many profiles match, "
    "open the first profile and report their record count, then reopen history "
    "and report its single new entry.",
    # 14 — login + profile editing + dashboard
    "Log in as alice.j@test.com (password TestPass123!). Open the profile; report "
    "the email, member-since date, display name, affiliation and research "
    "interests. Edit the profile: set affiliation to MIT CSAIL, research "
    "interests to graph learning and attention, display name to your own choice; "
    "save and report the updated values. Open the dashboard; report the watched "
    "author and venue counts and the recent searches. Open the watchlist; report "
    "the watched authors' names. Restore the affiliation to Stanford University, "
    "save, and report the final profile values.",
    # 15 — coauthor index chain (Guoliang Li)
    "From the home page author-search Guoliang Li and open the Tsinghua "
    "professor's profile; report his full dblp name, affiliation, record count "
    "and most productive year. Open his top coauthor (report name and joint "
    "count). Return; report how many coauthors the index lists. Open the coauthor "
    "with the second-highest joint count (report name and joint count). Open the "
    "professor's newest publication (report title, venue, pages), that venue's "
    "record count and busiest year, its newest edition's records, the edition's "
    "first record's title, that record's first author, their top coauthor, the "
    "coauthor's newest publication, and its venue's record count.",
    # 16 — homepage + browse + SIGMOD edition chain
    "From the home page report the five dblp statistics counters and the newest "
    "blog item's date and title. Browse the conference list; report how many "
    "venues start with A. Open the ACM SIGMOD Conference venue (report note line, "
    "records), its 2022 edition (report editors and records), that edition's "
    "first record (report title, authors, pages), the record's venue link (report "
    "where it leads and busiest year), that venue's newest edition, its first "
    "record's title and DOI, that record's first author, their top coauthor, and "
    "that coauthor's newest publication's venue. Search publications for sigmod "
    "year:2022; report the count and first title.",
    # 17 — cross-venue author chain
    "From the home page search publications for transformer year:2025; report the "
    "count. Open the first hit (report title and venue), its first author's "
    "profile (report record count and busiest year), and their newest publication "
    "(report title and venue). Open that venue (report record count and busiest "
    "year), its newest edition, and the edition's first record (report title). "
    "Open that record's first author (report record count) and their top "
    "coauthor's name. Search publications for attention year:2025; report the "
    "count, open the first hit (report title and venue), and that venue's record "
    "count and busiest year.",
    # 18 — login + research session with saving
    "Log in as bob.c@test.com (password TestPass123!). Search publications for "
    "learned index; report the count. Open the first hit's record (report DOI and "
    "venue) and save it to your DB reading list collection. Search venues for "
    "proceedings, open the VLDB Endowment venue (report record count and top "
    "frequent author) and add it to your watchlist. Open saved papers; report the "
    "collection contents, export it and report the entry count. Open the "
    "watchlist; report every watched venue, remove the VLDB Endowment venue and "
    "report what remains.",
    # 19 — author pagination + Min Zhang homonyms
    "From the home page author-search Zhang; report how many profiles match. Open "
    "results page two; report the first profile's name and record count. Open "
    "that profile (report busiest year), their top coauthor (report name and "
    "joint count), that coauthor's newest publication, and its venue's record "
    "count. Author-search Min Zhang; report how many profiles match, open the one "
    "with the most records (report full dblp name and record count), their newest "
    "publication, that venue's record count and busiest year, its newest "
    "edition's records, the edition's first record's title, and that record's "
    "first author's record count.",
]


def main():
    rows = []
    for i, ques in enumerate(TASKS):
        words = len(ques.split())
        assert words <= 100, f"task {i} too long: {words} words"
        rows.append({
            "web_name": NAME,
            "id": f"dblp--{i}",
            "ques": ques,
            "web": WEB,
            "upstream_url": UPSTREAM,
        })
    with open(OUT, "w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    print(f"tasks.jsonl: {len(rows)} tasks "
          f"({min(len(t.split()) for t in TASKS)}-"
          f"{max(len(t.split()) for t in TASKS)} words)")


if __name__ == "__main__":
    main()
