#!/usr/bin/env python3
"""Reviewer-authored judge_rubrics for tasks.jsonl (review track).

Re-freezes the judge_rubric of every task as reviewer-authored English pure
rules (umich r2 convention): the five original keys (web_name, id, ques,
web, upstream_url) and verifier_path stay byte-identical; no answer key is
ever added; rubrics state judging procedure only and never leak answer
values. Idempotent: run from sites/yahoo_finance.

    python3 scripts_dev/append_rubrics.py
"""
import json
from pathlib import Path

TASKS = Path(__file__).resolve().parent.parent / 'tasks.jsonl'

FACTS = {
 0: "Apple's sector; Apple's 52-week range; Apple's profit margin and "
    "1-year target estimate from the Statistics tab; the company's website "
    "and headquarters city from the Profile tab; the watchlist symbol "
    "count; Apple's last price on the watchlist; the new alert's status; "
    "Alice's total alert count",
 1: "the Day Gainers preset's top symbol with its price and percent "
    "change; the first custom-filter result's symbol and industry; the "
    "watchlist symbols after the addition",
 2: "the September 24 company with the biggest positive EPS surprise with "
    "its EPS estimate, reported EPS and surprise percent; how many "
    "after-market-close events remain that week; Costco's call time and "
    "EPS estimate; Dana's total alert count",
 3: "the sector with the largest aggregate market cap, its day percent "
    "change and its top loser; that sector's industry with the most "
    "companies and how many companies it has; the largest company's "
    "trailing P/E, forward dividend rate and yield, and 50-day average; "
    "the new alert's status; the watchlist count",
 4: "how many articles match the Nvidia news search; the most recent "
    "article's publisher, related tickers and author; the Economy topic's "
    "first article title and publisher; the new alert's status; Dana's "
    "total alert count",
 5: "the top three trending symbols with each percent change; the number "
    "one symbol's market cap, 52-week range, trailing P/E and 50-day "
    "average; the number three symbol's market cap; the watchlist symbol "
    "count; Carol's total alerts",
 6: "AMD's trailing P/E and profit margin; NVDA's trailing P/E and profit "
    "margin; which company has the lower P/E; the new alert's status; "
    "Bob's watchlist symbols",
 7: "the most-traded Most Actives symbol with its volume and percent "
    "change; its closing price on the most recent and first captured "
    "days; its 50-day average; the company's industry; the watchlist "
    "symbols",
 8: "how many articles match the buyback news search; the most recent "
    "article's publisher and author; Nvidia's closing price, percent change "
    "and trading volume as stated in the article text; the Earnings topic's "
    "only article title; the watchlist symbol count",
 9: "the latest fiscal year end date, total revenue and net income from "
    "the Financials tab; the PEG ratio and beta from the Statistics tab; "
    "the employee count from the Profile tab; the watchlist symbols; how "
    "many articles match the Apple news search and the newest article's "
    "publisher and author",
 10: "Coca-Cola's sector, industry, employee count and website; its "
     "forward dividend rate and yield; PepsiCo's profit margin and "
     "trailing P/E; the PEP alert status; how many symbols Bob watches",
 11: "which day of next week has the most events and how many; which day "
     "of this week has the most events and how many; Apple's next "
     "earnings date; its 1-year target estimate and 50-day average from "
     "the Statistics tab; the new alert's status; Dana's total alerts",
 12: "the initial watchlist symbols; Merck's trailing P/E and 52-week "
     "range; the final watchlist symbols; the new alert's status",
 13: "each initial alert's symbol, direction, threshold and status; the "
     "new TSLA alert's status; Alice's final alert count; Tesla's 50-day "
     "average",
 14: "the home page Day Gainers top symbol with its percent change; the "
     "first three filtered symbols with their changes; the first result's "
     "52-week change; Bob's watchlist symbols",
 15: "the quote symbols matching a bitcoin search; Bitcoin USD's price, "
     "market cap and 52-week range; how many stablecoin articles match; "
     "the most recent article's publisher and author; the three firms that "
     "handle the stablecoin's reserves as stated in the article text; the "
     "alert's status; Dana's watchlist symbol count",
 16: "how many Healthcare companies are listed; which industry has the "
     "most members; the largest and second largest companies' trailing "
     "P/E and profit margin; the alert status; the watchlist count",
 17: "Microsoft's closing price on the most recent and first captured "
     "days; its 50-day and 200-day moving averages; how many symbols "
     "Alice's watchlist lists; the new alert's status and Alice's total "
     "alerts",
 18: "how many articles match the inflation news search; the most recent "
     "article's publisher and author; the Gold futures price and percent "
     "change; the alert's status; Carol's watchlist symbol count",
 19: "the first three Utilities symbols with their dividend yields; the "
     "third result's dividend yield, market cap and next earnings date; "
     "how many alerts remain after the deletion; the watchlist symbol "
     "count",
}

TEMPLATE = (
 "Judge whether the agent completed this single user goal: {ques} "
 "Judging rules: (1) Accept equivalent natural prose, lists or tables. "
 "(2) Every reported fact must match the visible content of the pages the "
 "browser evidence shows the agent visited; for this task the required "
 "facts are: {facts}. (3) The required saved-state change is exactly the "
 "one the task text requests; unrelated records must be preserved. "
 "(4) Do not require an arbitrary action sequence or minimum step count. "
 "(5) Fail the attempt if it contradicts any required fact, if required "
 "pages are missing from the browser evidence, or if the saved state does "
 "not match the requested change.")


def main():
    lines = TASKS.read_text(encoding='utf-8').splitlines()
    out = []
    for line in lines:
        row = json.loads(line)
        idx = int(row['id'].rsplit('--', 1)[1])
        prefix = line[:line.index('"verifier_path"')]
        # byte-identical five-key prefix + verifier_path value
        vstart = line.index('"verifier_path"')
        vend = line.index('"judge_rubric"')
        verifier_segment = line[vstart:vend]
        assert verifier_segment.rstrip().endswith(',')
        new_rubric = TEMPLATE.format(ques=row['ques'], facts=FACTS[idx])
        new_line = (prefix + verifier_segment +
                    json.dumps('judge_rubric') + ': ' +
                    json.dumps(new_rubric) + '}')
        # sanity: five-key prefix bytes unchanged, verifier_path unchanged
        assert new_line[:vend] == line[:vend]
        out.append(new_line)
    TASKS.write_text('\n'.join(out) + '\n', encoding='utf-8')
    print(f're-froze {len(out)} reviewer rubrics; 5-key prefix and '
          f'verifier_path bytes preserved')


if __name__ == '__main__':
    main()
