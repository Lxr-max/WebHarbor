#!/usr/bin/env python3
"""Append verifier_path + judge_rubric to tasks.jsonl (reviewer contract).

The original 5 contributor keys (web_name, id, ques, web, upstream_url) are
preserved byte-identically; only the two reviewer keys are appended. No answer
key is ever written. Rubrics are English, rules-only (they name the pages that
MUST be opened and the facts that MUST appear, never the values).
"""
import json
from pathlib import Path

TASKS = Path(__file__).resolve().parents[1] / "tasks.jsonl"

RUBRICS = {
    0: ("FACT CHECKPOINTS: The trajectory must open the weekend forecast tab for Toronto, Montréal and "
        "Halifax. The final answer must name the warmest of the three cities overall and give the "
        "probability of precipitation for EACH weekend day in that winning city. An answer that names a "
        "different winning city, omits a weekend-day PoP, or gives no city comparison is a FAIL. An empty "
        "answer is a FAIL."),
    1: ("FACT CHECKPOINTS: The trajectory must open the 14-day forecast tab of an Alberta ski area. The "
        "final answer must report the first date fresh snow is expected in that 14-day window, the "
        "approximate snowfall amount for that date, and the daytime high for that same date, all "
        "consistent with the ski area actually opened. An answer with no date, no amount, no high, or "
        "values inconsistent with the opened area's forecast is a FAIL. An empty answer is a FAIL."),
    2: ("FACT CHECKPOINTS: The trajectory must open the alerts index and the individual alert pages "
        "covering Winnipegosis and Dauphin (Manitoba). The final answer must state whether the two "
        "communities are under the same alert or different ones, the alert kind, when it expires, and "
        "what the bulletin recommends people do. An answer missing any of these four components is a "
        "FAIL. An empty answer is a FAIL."),
    3: ("FACT CHECKPOINTS: The trajectory must open The Weather Network news article about Polo cementing "
        "its status as one of the Pacific's most intense hurricanes (weather/severe category). The final "
        "answer must name the only hurricane on record in the eastern Pacific with a lower central "
        "pressure and give the title of the video embedded at the top of the article. A wrong hurricane "
        "name, a missing video title, or answering from memory without opening the article is a FAIL. An "
        "empty answer is a FAIL."),
    4: ("FACT CHECKPOINTS: The trajectory must switch the site to imperial units via the preferences "
        "toggle and open the current-conditions pages for Vancouver, Winnipeg, Moncton and Calgary. The "
        "final answer must name the warmest of the four cities and give its current temperature and wind "
        "speed in imperial units (°F / mph). Metric-only values, a different winning city, or no wind "
        "speed is a FAIL. An empty answer is a FAIL."),
    5: ("FACT CHECKPOINTS: The trajectory must sign in as bob.c@test.com, open the account page, and open "
        "the Whistler Blackcomb page. The final answer must identify which saved location was the odd one "
        "out, confirm it was removed, confirm Whistler Blackcomb was added, and give the total number of "
        "saved locations afterwards. The database after-state must show exactly that removal and "
        "addition for bob's account. A wrong count or a database that does not match the claim is a "
        "FAIL. An empty answer is a FAIL."),
    6: ("FACT CHECKPOINTS: The trajectory must open the vacation section and the December monthly "
        "averages for the two warmest international destinations. The final answer must name both "
        "destinations, say which of the two is warmer, and give that destination's average December "
        "daytime high. An answer with only one destination, no comparison, or no December high is a "
        "FAIL. An empty answer is a FAIL."),
    7: ("FACT CHECKPOINTS: The trajectory must open Toronto's hourly forecast. The final answer must say "
        "when rain is expected to start and when the last of the showers should clear, each anchored to a "
        "specific hour. An answer without a start hour or an end hour is a FAIL. An empty answer is a "
        "FAIL."),
    8: ("FACT CHECKPOINTS: The trajectory must open the radar maps page, the current-conditions pages of "
        "the two Ontario radar cities, and the active alerts page. The final answer must give the number "
        "of radar cities, name the province(s) with more than one radar city, say which of the two "
        "Ontario radar cities is warmer right now, and state whether Ontario has any active weather "
        "alerts. Any missing component is a FAIL. An empty answer is a FAIL."),
    9: ("FACT CHECKPOINTS: The trajectory must open Scott Sutherland's article about the Harvest Moon "
        "(science/space category). The final answer must give the article's exact headline, the exact "
        "date and time the article says the Moon will be at its fullest, and what the September full "
        "moon is traditionally named after according to the article. A paraphrased headline, a missing "
        "time, or answering from memory is a FAIL. An empty answer is a FAIL."),
    10: ("FACT CHECKPOINTS: The trajectory must open the 7-day forecast tab of an Alberta golf course. "
         "The final answer must recommend a specific best day (lowest chance of precipitation) and give "
         "that day's forecast high, consistent with the course actually opened. An answer with no day, "
         "no high, or values inconsistent with the opened course is a FAIL. An empty answer is a FAIL."),
    11: ("FACT CHECKPOINTS: The trajectory must open the video section with the Animals and Weather "
         "playlist. The final answer must give the title and exact duration of the longest video in that "
         "playlist and the title of the shortest video in the same playlist. A missing duration, a wrong "
         "extreme, or titles from a different playlist is a FAIL. An empty answer is a FAIL."),
    12: ("FACT CHECKPOINTS: The trajectory must open the weekend forecast tabs of both Alberta Beach at "
         "Lac Ste. Anne and Aspen Beach Provincial Park on Gull Lake. The final answer must say which "
         "beach looks warmer and drier and whether rain should be expected at either one. An answer "
         "without a comparison or without the rain outlook is a FAIL. An empty answer is a FAIL."),
    13: ("FACT CHECKPOINTS: The trajectory must open Baker Lake's 14-day forecast. The final answer must "
         "give the coldest daytime high in the stretch with its date, the warmest daytime high with its "
         "date, and whether any snow is expected. A missing extreme, a missing date, or no snow verdict "
         "is a FAIL. An empty answer is a FAIL."),
    14: ("FACT CHECKPOINTS: The trajectory must open the registration page, create the account "
         "weather_fan2026, open the vacation section, and save three locations (Toronto, a ski resort, a "
         "vacation destination). The final answer must name the three saved locations. The database "
         "after-state must contain exactly one new user with that username and exactly three saved "
         "locations for it, one being Toronto and one being a ski resort. Any other database delta, a "
         "missing location, or a wrong count is a FAIL. An empty answer is a FAIL."),
    15: ("FACT CHECKPOINTS: The trajectory must open the active alerts page, filter to the province with "
         "the most alerts, and open at least one of that province's alert detail pages. The final answer "
         "must name the province with the most alerts, the dominant alert kind there, and what the "
         "bulletins recommend people do. Any missing component is a FAIL. An empty answer is a FAIL."),
    16: ("FACT CHECKPOINTS: The trajectory must open the El Niño and La Niña explore hub and the article "
         "about El Niño possibly delaying Canada's first frost. The final answer must state when the "
         "article says Prairie communities typically see their average first frost and which parts of "
         "Canada could see frost arrive later than usual this season. An answer missing either fact or "
         "answering without opening the article is a FAIL. An empty answer is a FAIL."),
    17: ("FACT CHECKPOINTS: The trajectory must open the current-conditions pages of Toronto, Halifax, "
         "Charlottetown, Winnipeg and Calgary. The final answer must rank all five cities from warmest "
         "to coldest, giving each city's current temperature and sky condition. A missing city, a "
         "missing temperature or condition, or a wrong ordering is a FAIL. An empty answer is a FAIL."),
    18: ("FACT CHECKPOINTS: The trajectory must open the article about the 'road-trip ruiner' invasive "
         "plant (nature category). The final answer must give the article's exact headline, the news "
         "category and subcategory it is filed under, and the author. A paraphrased headline, a wrong "
         "category/subcategory, or a wrong author is a FAIL. An empty answer is a FAIL."),
    19: ("FACT CHECKPOINTS: The trajectory must open Banff Community High School's forecast page and its "
         "hourly tab. The final answer must describe tomorrow's expected conditions during school hours, "
         "the daytime high, and whether any precipitation is in the forecast. An answer missing the "
         "conditions, the high, or the precipitation verdict is a FAIL. An empty answer is a FAIL."),
}


def main():
    raw = TASKS.read_text(encoding="utf-8").splitlines()
    assert len(raw) == 20, len(raw)
    out = []
    for i, line in enumerate(raw):
        row = json.loads(line)
        assert list(row.keys()) == ["web_name", "id", "ques", "web", "upstream_url"], row.keys()
        # byte-identical prefix surgery: keep the original 5-key JSON object verbatim
        # and splice the two reviewer keys in before the closing brace
        assert line.endswith("}")
        new_keys = json.dumps({
            "verifier_path": f"sites/the_weather_network/verify/verify_{i}.py",
            "judge_rubric": RUBRICS[i],
        }, ensure_ascii=False)[1:-1]
        out.append(line[:-1] + ", " + new_keys + "}")
    TASKS.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("appended verifier_path + judge_rubric to", TASKS)


if __name__ == "__main__":
    main()
