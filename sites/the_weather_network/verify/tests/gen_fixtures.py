#!/usr/bin/env python3
"""Generate tests/fixtures_data.py from the reviewer's honest walk JSONs."""
import json
import sys
from pathlib import Path

WALKS = Path("/data/zhaoyang-user-projects/websyn/wh-twn-review-evidence/walks")
BASE = "http://localhost:46099"

KIND_TO_ACTION = {"NAV": "click", "FILL": "input", "SELECT": "select",
                  "SUBMIT": "click", "SCAN": "observe", "READ": "observe"}

ANSWERS = {
    0: ("Toronto looks warmest overall. Weekend outlooks: Toronto Sat 22°/13° (P.O.P. 20%, none expected), "
        "Sun 23°/14° (P.O.P. 30%); Montréal Sat 22°/14° (P.O.P. 30%), Sun 20° (P.O.P. 40%, <1 mm); "
        "Halifax Sat 17° (P.O.P. 30%), Sun 17° (P.O.P. 100%, ~5 mm rain). "
        "In the winning city Toronto the probability of precipitation is 20% on Saturday and 30% on Sunday."),
    1: ("Banff Sunshine (Alberta): the first date fresh snow is expected is Saturday, September 26 — "
        "Light snow with under 1 cm (<1 cm) accumulation — and the daytime high for that date is 4°C."),
    2: ("Winnipegosis and Dauphin are under different alerts (two separate records), but both are "
        "High Water Level warnings for the Mossey River area, issued Wed 3:53 PM Sep. 23 and both "
        "expiring Wed 9:00 PM Sep. 30. The bulletin recommends people be aware and exercise caution "
        "near waterways, not attempt to cross fast flowing waters or waters of unknown depth, "
        "avoid flooded areas, and follow directions by the local authorities."),
    3: ("Hurricane Patricia is the only hurricane on record in the eastern Pacific with a lower "
        "central pressure (872 mb in October 2015). The video embedded at the top of the article "
        "is 'Hurricane Polo, one of the Eastern Pacific's most intense hurricanes'."),
    4: ("With the site switched to imperial units, Winnipeg is the warmest of the four cities right "
        "now at 63°F (Light rain), with a wind speed of 16 mph. Vancouver is 57°F, Moncton 52°F, "
        "Calgary 43°F."),
    5: ("Bob's saved locations list had three BC entries (Vancouver, Victoria, Kelowna) plus "
        "Banff National Park - Banff, the odd one out (an Alberta park). After removing it and "
        "adding Whistler Blackcomb, Bob has 4 locations saved in total."),
    6: ("The two warmest international destinations in the vacation section by December monthly "
        "averages are Santo Domingo (Dominican Republic) and Cancún (Mexico). Santo Domingo is "
        "warmer, with a December average daytime high of 29°C (Cancún is 27°C)."),
    7: ("Toronto's hourly forecast shows rain starting at 11 PM tonight (Cloudy with showers from "
        "11pm), with the last of the showers around 5 AM; by 6 AM the showers have cleared. "
        "So it is safe to paint before 11 PM, and you will need to stop around then."),
    8: ("You can view radar for 7 cities. Two provinces have more than one radar city: Ontario "
        "(Toronto and Ottawa) and British Columbia (Vancouver and Victoria). Of the two Ontario "
        "radar cities, Toronto is warmer right now (18°C vs Ottawa's 13°C). Ontario currently "
        "has no active weather alerts."),
    9: ("The exact headline is 'The Harvest Moon lights up our night sky this weekend'. The article "
        "says the Moon will be at its fullest at 12:49 p.m. EDT on Saturday, September 26. The "
        "September full moon is traditionally named after the corn harvest — the Corn Moon."),
    10: ("Acme Golf Club (Alberta): the best day for your dad to play is Sunday, September 27 or "
         "Monday, September 28 — both have the lowest chance of precipitation at 20% with 0 mm "
         "expected. Sunday's forecast high is 14°C (Monday reaches 17°C)."),
    11: ("The longest video in the Animals and Weather playlist is 'All about bees: What to do when "
         "you get stung, and more' with an exact duration of 4:00. The shortest video in the same "
         "playlist is 'Good samaritan gives water to bat struggling during heat wave' (0:50)."),
    12: ("Aspen Beach Provincial Park on Gull Lake looks warmer and drier: Saturday 10°C vs Alberta "
         "Beach's 9°C (both P.O.P. 30%), and Sunday both reach 14°C, Sunny with 10% P.O.P. "
         "No rain is expected at either beach this weekend."),
    13: ("Baker Lake's 14-day forecast: the coldest daytime high is 3°C on October 4 (also 3°C on "
         "October 10); the warmest daytime high is 7°C on Monday, September 28. Snow is expected — "
         "September 27's forecast carries '<1 cm snow' with the rain."),
    14: ("I created the account weather_fan2026 and saved three locations: Toronto (ON), "
         "Whistler Blackcomb (the ski resort I would like to visit this winter), and Havana, Cuba "
         "(my dream vacation destination)."),
    15: ("Alberta has the most active alerts (40 of the 51). The dominant kind is frost — every "
         "Alberta alert is a Yellow Advisory - Frost. The bulletins recommend taking preventative "
         "measures to protect cold-sensitive plants, trees and crops, and covering up plants, "
         "especially those in frost-prone areas."),
    16: ("The article says many Prairie communities see their average first frost around the middle "
         "of September. Thanks to El Niño, frost and hard freezes could arrive later than usual "
         "across the southern half of Canada this season."),
    17: ("Warmest to coldest right now: Toronto 18°C (Clear), Winnipeg 17°C (Light rain), Halifax "
         "15°C (Mostly cloudy), Charlottetown 12°C (Clear), Calgary 6°C (Mostly cloudy)."),
    18: ("The exact headline is \"'Once you see it, you can't unsee it': The 'road-trip ruiner' "
         "plant is back\". It is filed under the Nature category, Habitats subcategory, and was "
         "written by Cheryl Santa Maria."),
    19: ("Tomorrow (Sunday, September 27) during school hours at Banff Community High School the "
         "forecast is mainly sunny, warming from -1°C at 9 AM to 11°C by mid-afternoon. The "
         "daytime high is 11°C and no precipitation is in the forecast (P.O.P. 10%, 0 mm) — "
         "dry outdoor recess."),
}

SQL = {
    5: ["DELETE FROM saved_locations WHERE user_id = 2 AND loc_id = 190;",
        "INSERT INTO saved_locations (id, user_id, loc_id, created_at) VALUES (16, 2, 329, '2026-09-26 21:30:00');"],
    14: ["INSERT INTO users (id, username, email, password_hash, display_name, unit, created_at) "
         "VALUES (5, 'weather_fan2026', 'weather_fan2026@test.com', "
         "'$2b$12$SWYN0gslqt1D7QvAZwQ87.aPrk9a4fNQhJq2U2FypvTFgbXSbFlly', 'weather_fan2026', 'metric', '2026-09-26 21:30:00');",
         "INSERT INTO saved_locations (id, user_id, loc_id, created_at) VALUES (16, 5, 57, '2026-09-26 21:30:00');",
         "INSERT INTO saved_locations (id, user_id, loc_id, created_at) VALUES (17, 5, 329, '2026-09-26 21:30:00');",
         "INSERT INTO saved_locations (id, user_id, loc_id, created_at) VALUES (18, 5, 82, '2026-09-26 21:30:00');"],
}

START_PATHS = {n: "/en" for n in range(20)}


def slug_url(url):
    return url.replace("http://127.0.0.1:46099", "")


def main():
    specs = {}
    for n in range(20):
        walk = json.loads((WALKS / f"T{n}_walk.json").read_text())
        steps = []
        for s in walk["steps"]:
            action = KIND_TO_ACTION.get(s["kind"], "click")
            steps.append((action, slug_url(s["url"])))
        # dedupe consecutive identical (action, url) pairs but keep ordering meaningful
        dedup = []
        for st in steps:
            if dedup and dedup[-1] == st:
                continue
            dedup.append(st)
        specs[n] = dict(steps=dedup, answer=ANSWERS[n], sql=SQL.get(n, []))
    wrong = {
        0: "Halifax looks warmest overall; the probability of precipitation there is 100% on Saturday and 90% on Sunday.",
        1: "Nakiska Ski Area: the first date fresh snow is expected is October 2, with about 5 cm falling and a daytime high of 12°C.",
        2: "Winnipegosis and Dauphin are under the same single alert, a Frost advisory, which expires Thursday at noon.",
        3: "Hurricane Otis is the only eastern Pacific hurricane with a lower central pressure; the top video is 'Inside the eye of Polo'.",
        4: "Vancouver is the warmest at 57°F with winds of 7 mph.",
        5: "Bob has 5 locations saved in total now.",
        6: "Cancún is the warmer of the two, with a December average high of 31°C.",
        7: "Rain starts at 3 PM and the showers clear by 8 PM.",
        8: "You can view radar for 5 cities; only Quebec has more than one; Ottawa is warmer; Ontario has 12 active alerts.",
        9: "The headline is 'Harvest Moon 2026'; the Moon is fullest at 8:30 PM on Sunday the 27th; it is named after the wheat harvest.",
        10: "The best day is Friday with a 60% chance of precipitation and a high of 25°C.",
        11: "The longest video is 'Fat Bear Week is here' at 1:27, and the shortest is a 30-second clip.",
        12: "Alberta Beach looks warmer and drier; heavy rain is expected at Aspen Beach.",
        13: "The coldest daytime high is -5°C on October 9 and the warmest is 12°C on September 29; no snow is expected.",
        14: "I created the account and saved Toronto, Vancouver and Halifax.",
        15: "Manitoba has the most alerts; they are all rainfall warnings recommending people carry umbrellas.",
        16: "Prairie communities see their first frost in late October, and the territories will see frost arrive later this season.",
        17: "Coldest to warmest: Calgary 6°C, Charlottetown 12°C, Halifax 15°C, Winnipeg 17°C, Toronto 18°C.",
        18: "The headline is 'Invasive plant warning'; it is filed under Weather > Forecasts and written by Scott Sutherland.",
        19: "Tomorrow will be rainy with a high of 4°C and snow expected during school hours.",
    }
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "tests/fixtures_data.py")
    with out.open("w") as f:
        f.write('"""Frozen fixtures for the_weather_network verifier tests.\n\n')
        f.write('SPECS: per-task honest trajectories (action + URL sequences + final answers)\n')
        f.write('extracted verbatim from the reviewer\'s live Playwright walks of the review\n')
        f.write('container (wh-twn-review); SQL: the exact DB after-state deltas the site\n')
        f.write('writes for that walk; WRONG_ANSWERS: plausible-but-wrong answers for the\n')
        f.write('adversarial negative tests. No LLM.\n"""\n\n')
        f.write("BASE = " + json.dumps(BASE) + "\n\nSPECS = {\n")
        for k in sorted(specs):
            f.write(f"    {k}: " + json.dumps(specs[k], indent=1).replace('\n', '\n    ') + ",\n")
        f.write("}\n\nWRONG_ANSWERS = {\n")
        for n in range(20):
            f.write(f"    {n}: " + json.dumps(wrong[n]) + ",\n")
        f.write("}\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
