"""Frozen fixtures for the_weather_network verifier tests (r2 re-sync).

SPECS: per-task honest trajectories (action + URL sequences + final answers)
extracted verbatim from the reviewer's live Playwright walks of the r2
re-review container (wh-twn-rereview) against the contribution @ 8af51be4;
SQL: the exact DB after-state deltas the site writes for that walk;
WRONG_ANSWERS: plausible-but-wrong answers for the adversarial negative
tests. No LLM.
"""

BASE = "http://localhost:46099"

SPECS = {
 0: {
  "steps": [
   [
    "click",
    "/en/city/ca/ontario/toronto/current"
   ],
   [
    "click",
    "/en/city/ca/ontario/toronto/weekend"
   ],
   [
    "observe",
    "/en/city/ca/ontario/toronto/weekend"
   ],
   [
    "click",
    "/en/city/ca/quebec/montreal/current"
   ],
   [
    "click",
    "/en/city/ca/quebec/montreal/weekend"
   ],
   [
    "observe",
    "/en/city/ca/quebec/montreal/weekend"
   ],
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/city/ca/nova-scotia/halifax/current"
   ],
   [
    "click",
    "/en/city/ca/nova-scotia/halifax/weekend"
   ],
   [
    "observe",
    "/en/city/ca/nova-scotia/halifax/weekend"
   ]
  ],
  "answer": "Toronto looks warmest overall. Weekend outlooks: Toronto Sat 22°/13° (P.O.P. 20%, none expected), Sun 23°/14° (P.O.P. 30%); Montréal Sat 22°/14° (P.O.P. 30%), Sun 20° (P.O.P. 40%, <1 mm); Halifax Sat 17° (P.O.P. 30%), Sun 17° (P.O.P. 100%, ~5 mm rain). In the winning city Toronto the probability of precipitation is 20% on Saturday and 30% on Sunday.",
  "sql": []
 },
 1: {
  "steps": [
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/ski/ca/alberta/banff-sunshine/current"
   ],
   [
    "observe",
    "/en/ski/ca/alberta/banff-sunshine/current"
   ],
   [
    "click",
    "/en/ski/ca/alberta/banff-sunshine/14-days"
   ],
   [
    "observe",
    "/en/ski/ca/alberta/banff-sunshine/14-days"
   ],
   [
    "click",
    "/en/ski/ca/alberta/banff-sunshine/weekend"
   ],
   [
    "observe",
    "/en/ski/ca/alberta/banff-sunshine/weekend"
   ]
  ],
  "answer": "Banff Sunshine right now: 3°C and Clear. In the 14-day outlook the first fresh snow is expected on Saturday, September 26 — light snow with under 1 cm (<1 cm) — and the daytime high that date is 4°C. The coldest overnight low in the window is -6°C, and the warmest day of the two weeks is Monday, October 5 at 12°C. This weekend: Saturday light snow, 4°C with 60% PoP; Sunday mainly sunny, 6°C with 10% PoP.",
  "sql": []
 },
 2: {
  "steps": [
   [
    "click",
    "/en/alerts/ca"
   ],
   [
    "select",
    "/en/alerts/ca?region=MB"
   ],
   [
    "observe",
    "/en/alerts/ca?region=MB"
   ],
   [
    "click",
    "/en/alerts/ca/W_CSD4617073"
   ],
   [
    "observe",
    "/en/alerts/ca/W_CSD4617073"
   ],
   [
    "click",
    "/en/alerts/ca?region=MB"
   ],
   [
    "click",
    "/en/alerts/ca/W_CSD4617048"
   ],
   [
    "observe",
    "/en/alerts/ca/W_CSD4617048"
   ]
  ],
  "answer": "Winnipegosis and Dauphin are under different (separate) alert records, but both are High Water Level advisories for the Mossey River area. Each was issued Wednesday 3:53 PM Sep. 23 and both expire Wednesday 9:00 PM Sep. 30 — so yes, the two alerts end at the same time. The bulletin recommends people be aware and exercise caution near waterways, not attempt to cross fast-flowing or unknown-depth water, avoid flooded areas and follow directions from local authorities.",
  "sql": []
 },
 3: {
  "steps": [
   [
    "click",
    "/en/news"
   ],
   [
    "click",
    "/en/news/weather/severe"
   ],
   [
    "observe",
    "/en/news/weather/severe"
   ],
   [
    "click",
    "/en/news/weather/severe/polo-cements-its-status-as-one-of-the-pacifics-most-intense-hurricanes"
   ],
   [
    "observe",
    "/en/news/weather/severe/polo-cements-its-status-as-one-of-the-pacifics-most-intense-hurricanes"
   ],
   [
    "click",
    "/en/news/weather/severe"
   ],
   [
    "observe",
    "/en/news/weather/severe"
   ],
   [
    "click",
    "/en/news/weather/severe/inside-a-beast-see-polo-growth-into-a-powerful-historic-hurricane-mexico"
   ],
   [
    "observe",
    "/en/news/weather/severe/inside-a-beast-see-polo-growth-into-a-powerful-historic-hurricane-mexico"
   ]
  ],
  "answer": "Hurricane Patricia is the only hurricane on record in the eastern Pacific with a lower central pressure — 872 mb (October 2015), with maximum winds of about 345 km/h. Polo reached peak intensity on Tuesday, Sept. 22 with maximum sustained winds of 285 km/h. According to NOAA, Polo's minimum central pressure dropped by 88 mb in 24 hours. The video embedded at the top of the 'Polo cements' article is 'Hurricane Polo, one of the Eastern Pacific's most intense hurricanes', and the video at the top of the 'Inside the eye' article is 'See the view inside Hurricane Polo as it became a monster storm'. The eye-footage piece was written by Nathan Howes and published on Sep. 26, 2026.",
  "sql": []
 },
 4: {
  "steps": [
   [
    "click",
    "/en"
   ],
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/city/ca/british-columbia/vancouver/current"
   ],
   [
    "observe",
    "/en/city/ca/british-columbia/vancouver/current"
   ],
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/city/ca/manitoba/winnipeg/current"
   ],
   [
    "observe",
    "/en/city/ca/manitoba/winnipeg/current"
   ],
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/city/ca/new-brunswick/moncton/current"
   ],
   [
    "observe",
    "/en/city/ca/new-brunswick/moncton/current"
   ],
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/city/ca/alberta/calgary/current"
   ],
   [
    "observe",
    "/en/city/ca/alberta/calgary/current"
   ]
  ],
  "answer": "With the site switched to imperial units, Winnipeg is the warmest of the four cities right now at 63°F (Light rain), with a wind speed of 16 mph. Vancouver is 57°F, Moncton 52°F, Calgary 43°F.",
  "sql": []
 },
 5: {
  "steps": [
   [
    "click",
    "/en/account/sign-in"
   ],
   [
    "input",
    "/en/account/sign-in"
   ],
   [
    "click",
    "/en/account"
   ],
   [
    "observe",
    "/en/account"
   ],
   [
    "click",
    "/en/account"
   ],
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/ski/ca/british-columbia/whistler-blackcomb/current"
   ],
   [
    "click",
    "/en/account"
   ],
   [
    "observe",
    "/en/account"
   ]
  ],
  "answer": "The odd one out was Banff National Park - Banff (an Alberta park among Bob's three BC cities). After removing it and adding Whistler Blackcomb, Bob has 4 locations saved in total, and with his account units switched to imperial the account page shows Whistler Blackcomb at 52°F.",
  "sql": [
   "DELETE FROM saved_locations WHERE user_id = 2 AND loc_id = 190;",
   "INSERT INTO saved_locations (id, user_id, loc_id, created_at) VALUES (16, 2, 329, '2026-09-26 21:30:00');",
   "UPDATE users SET unit = 'imperial' WHERE id = 2;"
  ]
 },
 6: {
  "steps": [
   [
    "click",
    "/en/vacation"
   ],
   [
    "observe",
    "/en/vacation"
   ],
   [
    "click",
    "/en/vacation/do"
   ],
   [
    "observe",
    "/en/vacation/do"
   ],
   [
    "click",
    "/en/city/do/ozama/santo-domingo/current"
   ],
   [
    "click",
    "/en/city/do/ozama/santo-domingo/monthly"
   ],
   [
    "observe",
    "/en/city/do/ozama/santo-domingo/monthly"
   ],
   [
    "click",
    "/en/vacation/mx"
   ],
   [
    "observe",
    "/en/vacation/mx"
   ],
   [
    "click",
    "/en/city/mx/quintana-roo/cancun/current"
   ],
   [
    "click",
    "/en/city/mx/quintana-roo/cancun/monthly"
   ],
   [
    "observe",
    "/en/city/mx/quintana-roo/cancun/monthly"
   ],
   [
    "click",
    "/en/vacation/cu"
   ],
   [
    "observe",
    "/en/vacation/cu"
   ],
   [
    "click",
    "/en/city/cu/la-habana/havana/current"
   ],
   [
    "click",
    "/en/city/cu/la-habana/havana/monthly"
   ],
   [
    "observe",
    "/en/city/cu/la-habana/havana/monthly"
   ],
   [
    "click",
    "/en/vacation/bs"
   ],
   [
    "observe",
    "/en/vacation/bs"
   ],
   [
    "click",
    "/en/city/bs/new-providence/nassau/current"
   ],
   [
    "click",
    "/en/city/bs/new-providence/nassau/monthly"
   ],
   [
    "observe",
    "/en/city/bs/new-providence/nassau/monthly"
   ],
   [
    "click",
    "/en/vacation/au"
   ],
   [
    "observe",
    "/en/vacation/au"
   ],
   [
    "click",
    "/en/city/au/new-south-wales/sydney/current"
   ],
   [
    "click",
    "/en/city/au/new-south-wales/sydney/monthly"
   ],
   [
    "observe",
    "/en/city/au/new-south-wales/sydney/monthly"
   ],
   [
    "click",
    "/en/vacation/us"
   ],
   [
    "observe",
    "/en/vacation/us"
   ],
   [
    "click",
    "/en/city/us/alaska/anchorage/current"
   ],
   [
    "click",
    "/en/city/us/alaska/anchorage/monthly"
   ],
   [
    "observe",
    "/en/city/us/alaska/anchorage/monthly"
   ]
  ],
  "answer": "The two warmest international destinations in the vacation section by December monthly averages are Santo Domingo (Dominican Republic) and Cancún (Mexico). Santo Domingo is warmer, with a December average daytime high of 29°C (Cancún is 27°C).",
  "sql": []
 },
 7: {
  "steps": [
   [
    "click",
    "/en/city/ca/ontario/toronto/current"
   ],
   [
    "observe",
    "/en/city/ca/ontario/toronto/current"
   ],
   [
    "click",
    "/en/city/ca/ontario/toronto/hourly"
   ],
   [
    "observe",
    "/en/city/ca/ontario/toronto/hourly"
   ],
   [
    "click",
    "/en/city/ca/ontario/toronto/7-days"
   ],
   [
    "observe",
    "/en/city/ca/ontario/toronto/7-days"
   ]
  ],
  "answer": "Toronto right now: 18°C and Clear. The hourly forecast shows rain starting at 11 PM Sunday, with the last of the showers clearing by 5 AM Monday — 7 hours of rain in total, with the highest precipitation chance during them at 60%. Overnight during the rain it gets as cold as 14°C. The dry stretch before the rain arrives spans 12-23°C, and Monday afternoon warms back up to 20°C after the rain clears. In the 7-day outlook the day later in the week with the highest rain chance is Thursday, October 1 at 70% (5-10 mm expected) — that is when you would need to stop painting.",
  "sql": []
 },
 8: {
  "steps": [
   [
    "click",
    "/en/maps/radar"
   ],
   [
    "observe",
    "/en/maps/radar"
   ],
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/city/ca/ontario/ottawa/current"
   ],
   [
    "observe",
    "/en/city/ca/ontario/ottawa/current"
   ],
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/city/ca/ontario/toronto/current"
   ],
   [
    "observe",
    "/en/city/ca/ontario/toronto/current"
   ],
   [
    "click",
    "/en/alerts/ca"
   ],
   [
    "observe",
    "/en/alerts/ca"
   ]
  ],
  "answer": "You can view radar for 7 cities. Ontario and British Columbia are the provinces with more than one radar city. Of the two Ontario radar cities, Toronto is warmer right now: Toronto 18°C and Clear, Ottawa 13°C and Partly cloudy. Across Canada 51 alerts are in effect, and Ontario has no active weather alerts.",
  "sql": []
 },
 9: {
  "steps": [
   [
    "click",
    "/en/news"
   ],
   [
    "click",
    "/en/news/science"
   ],
   [
    "click",
    "/en/news/science/space"
   ],
   [
    "observe",
    "/en/news/science/space"
   ],
   [
    "click",
    "/en/news/science/space/full-corn-moon-harvest-moon-lights-up-our-nights-this-weekend"
   ],
   [
    "observe",
    "/en/news/science/space/full-corn-moon-harvest-moon-lights-up-our-nights-this-weekend"
   ],
   [
    "click",
    "/en/video/JDBq6DC8"
   ],
   [
    "observe",
    "/en/video/JDBq6DC8"
   ],
   [
    "click",
    "/en/news/science/space/full-corn-moon-harvest-moon-lights-up-our-nights-this-weekend"
   ],
   [
    "click",
    "/en/news/weather/seasonal/autumn-the-season-of-meteor-showers-is-about-to-begin-for-2026"
   ],
   [
    "observe",
    "/en/news/weather/seasonal/autumn-the-season-of-meteor-showers-is-about-to-begin-for-2026"
   ]
  ],
  "answer": "The exact headline is 'The Harvest Moon lights up our night sky this weekend'. The article says the Moon will be at its fullest at 12:49 p.m. EDT on Saturday, September 26. The September full moon is traditionally named after the corn harvest (the Corn Moon), and NASA scientists informally also call it the GRAIL Moon and the LADEE Moon. The video embedded at the top of the article is 'Your guide to September's night sky'. The linked meteor-shower article says the Draconids peak first this fall.",
  "sql": []
 },
 10: {
  "steps": [
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/golf/ca/alberta/acme-golf-club/current"
   ],
   [
    "observe",
    "/en/golf/ca/alberta/acme-golf-club/current"
   ],
   [
    "click",
    "/en/golf/ca/alberta/acme-golf-club/7-days"
   ],
   [
    "observe",
    "/en/golf/ca/alberta/acme-golf-club/7-days"
   ],
   [
    "click",
    "/en/golf/ca/alberta/acme-golf-club/weekend"
   ],
   [
    "observe",
    "/en/golf/ca/alberta/acme-golf-club/weekend"
   ]
  ],
  "answer": "Acme Golf Club (Alberta) right now: cloudy with clear breaks. The best day for dad to play is Sunday, September 27 or Monday, September 28 — both carry the lowest precipitation chance at 20% with 0 mm expected; Sunday's forecast high is 14°C (Monday reaches 17°C). The warmest day of the seven is Tuesday, September 29 at 20°C, 5 days show a precipitation chance above 20 percent, and the coming weekend looks showery Saturday (9°, 70% PoP) then sunny Sunday (14°, 20% PoP).",
  "sql": []
 },
 11: {
  "steps": [
   [
    "click",
    "/en/video"
   ],
   [
    "observe",
    "/en/video"
   ],
   [
    "click",
    "/en/video/1LfM4CFg"
   ],
   [
    "observe",
    "/en/video/1LfM4CFg"
   ],
   [
    "click",
    "/en/video"
   ],
   [
    "observe",
    "/en/video"
   ]
  ],
  "answer": "The Animals and Weather playlist holds 50 videos. The longest is 'All about bees: What to do when you get stung, and more' with an exact duration of 4:00, and the shortest is 'Good samaritan gives water to bat struggling during heat wave' at 0:50. The longest video's page says Kim MacDonald and Rachel Schoutsen reveal everything about bees and what to do when you get stung. The Featured playlist's longest video is 'Fall Night Sky: Parade of meteor showers, plus a planet dance' at 3:37 — so the Animals and Weather playlist's longest video runs longer.",
  "sql": []
 },
 12: {
  "steps": [
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/beach/ca/alberta/alberta-beach-at-lac-ste-anne/current"
   ],
   [
    "click",
    "/en/beach/ca/alberta/alberta-beach-at-lac-ste-anne/weekend"
   ],
   [
    "observe",
    "/en/beach/ca/alberta/alberta-beach-at-lac-ste-anne/weekend"
   ],
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/beach/ca/alberta/aspen-beach-provincial-park-on-gull-lake/current"
   ],
   [
    "click",
    "/en/beach/ca/alberta/aspen-beach-provincial-park-on-gull-lake/weekend"
   ],
   [
    "observe",
    "/en/beach/ca/alberta/aspen-beach-provincial-park-on-gull-lake/weekend"
   ],
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/beach/ca/alberta/gregoire-lake-provincial-park-beach/current"
   ],
   [
    "click",
    "/en/beach/ca/alberta/gregoire-lake-provincial-park-beach/weekend"
   ],
   [
    "observe",
    "/en/beach/ca/alberta/gregoire-lake-provincial-park-beach/weekend"
   ]
  ],
  "answer": "Aspen Beach Provincial Park on Gull Lake is the warmest on Saturday at 10°C (Alberta Beach at Lac Ste. Anne 9°C, Gregoire Lake Provincial Park Beach 8°C). Gregoire Lake is the only beach expecting rain that day — about 5 mm with a 90% PoP — while the other two stay dry. All three beaches share the same Sunday outlook: Sunny, 14°C, 10% PoP.",
  "sql": []
 },
 13: {
  "steps": [
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/city/ca/nunavut/baker-lake/current"
   ],
   [
    "click",
    "/en/city/ca/nunavut/baker-lake/14-days"
   ],
   [
    "observe",
    "/en/city/ca/nunavut/baker-lake/14-days"
   ],
   [
    "click",
    "/en/city/ca/nunavut/baker-lake/monthly"
   ],
   [
    "observe",
    "/en/city/ca/nunavut/baker-lake/monthly"
   ],
   [
    "click",
    "/en/alerts/ca"
   ],
   [
    "select",
    "/en/alerts/ca?region=NU"
   ],
   [
    "observe",
    "/en/alerts/ca?region=NU"
   ],
   [
    "click",
    "/en/alerts/ca/W_WWCANU0006"
   ],
   [
    "observe",
    "/en/alerts/ca/W_WWCANU0006"
   ]
  ],
  "answer": "Baker Lake's warmest daytime high in the 14-day stretch is 7°C on Monday, September 28; the coldest overnight low is -3°C; the wettest day is Sunday, September 27 with 10-15 mm of rain. The monthly averages page gives September 28 a typical daytime high of 3°C, so the forecast is 4° warmer than average. Baker Lake is under a Yellow Warning - Rainfall right now, ending Sun 1:15 AM.",
  "sql": []
 },
 14: {
  "steps": [
   [
    "click",
    "/en/account/sign-in"
   ],
   [
    "click",
    "/en/account/register"
   ],
   [
    "input",
    "/en/account/register"
   ],
   [
    "click",
    "/en/account"
   ],
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/city/ca/ontario/toronto/current"
   ],
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/ski/ca/british-columbia/whistler-blackcomb/current"
   ],
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/city/cu/la-habana/havana/current"
   ],
   [
    "click",
    "/en/account"
   ],
   [
    "observe",
    "/en/account"
   ]
  ],
  "answer": "I created the account weather_fan2026 and saved three locations: Toronto (ON), Whistler Blackcomb (the ski resort I would like to visit this winter), and Havana, Cuba (my dream vacation destination).",
  "sql": [
   "INSERT INTO users (id, username, email, password_hash, display_name, unit, created_at) VALUES (5, 'weather_fan2026', 'weather_fan2026@test.com', '$2b$12$SWYN0gslqt1D7QvAZwQ87.aPrk9a4fNQhJq2U2FypvTFgbXSbFlly', 'weather_fan2026', 'metric', '2026-09-26 21:30:00');",
   "INSERT INTO saved_locations (id, user_id, loc_id, created_at) VALUES (16, 5, 57, '2026-09-26 21:30:00');",
   "INSERT INTO saved_locations (id, user_id, loc_id, created_at) VALUES (17, 5, 329, '2026-09-26 21:30:00');",
   "INSERT INTO saved_locations (id, user_id, loc_id, created_at) VALUES (18, 5, 82, '2026-09-26 21:30:00');"
  ]
 },
 15: {
  "steps": [
   [
    "click",
    "/en/alerts/ca"
   ],
   [
    "observe",
    "/en/alerts/ca"
   ],
   [
    "select",
    "/en/alerts/ca?region=AB"
   ],
   [
    "observe",
    "/en/alerts/ca?region=AB"
   ],
   [
    "click",
    "/en/alerts/ca/W_WWCAAB0034B"
   ],
   [
    "observe",
    "/en/alerts/ca/W_WWCAAB0034B"
   ],
   [
    "click",
    "/en/alerts/ca"
   ],
   [
    "select",
    "/en/alerts/ca?region=NU"
   ],
   [
    "observe",
    "/en/alerts/ca?region=NU"
   ],
   [
    "click",
    "/en/alerts/ca/W_WWCANU0006"
   ],
   [
    "observe",
    "/en/alerts/ca/W_WWCANU0006"
   ]
  ],
  "answer": "51 alerts are in effect across Canada. Alberta has the most (40), dominated by Yellow Advisory - Frost bulletins that recommend taking preventative measures to protect cold-sensitive plants — covering up plants, especially those in frost-prone areas. Nunavut has 3 active alerts, all Yellow Warning - Rainfall, expiring Sun 1:15 AM.",
  "sql": []
 },
 16: {
  "steps": [
   [
    "click",
    "/en/explore/el-nino-la-nina"
   ],
   [
    "observe",
    "/en/explore/el-nino-la-nina"
   ],
   [
    "click",
    "/en/news/weather/forecasts/el-nino-could-delay-persistent-frost-and-hard-freezes-across-canada"
   ],
   [
    "observe",
    "/en/news/weather/forecasts/el-nino-could-delay-persistent-frost-and-hard-freezes-across-canada"
   ],
   [
    "click",
    "/en/news/science/explainers/understanding-canadas-frost-zones-and-when-that-first-frost-may-hit"
   ],
   [
    "observe",
    "/en/news/science/explainers/understanding-canadas-frost-zones-and-when-that-first-frost-may-hit"
   ]
  ],
  "answer": "The first-frost article is filed under the Weather section (Forecasts). Prairie communities typically see their average first frost around the middle of September, while southern Ontario, southern Quebec, the Atlantic provinces and B.C.'s Interior see theirs in October. The article calls a hard freeze -2°C or colder for several hours. Frost advisories have already been issued in portions of New Brunswick, Newfoundland, Quebec and Ontario this season. The linked frost-zones explainer says the coldest zone is Zone 0 (northern Canada), the mildest is Zone 9 (parts of Vancouver Island), the zones are based on a 30-year average, and meteorologist Kevin MacKay is quoted.",
  "sql": []
 },
 17: {
  "steps": [
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/city/ca/ontario/toronto/current"
   ],
   [
    "observe",
    "/en/city/ca/ontario/toronto/current"
   ],
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/city/ca/nova-scotia/halifax/current"
   ],
   [
    "observe",
    "/en/city/ca/nova-scotia/halifax/current"
   ],
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/city/ca/prince-edward-island/charlottetown/current"
   ],
   [
    "observe",
    "/en/city/ca/prince-edward-island/charlottetown/current"
   ],
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/city/ca/manitoba/winnipeg/current"
   ],
   [
    "observe",
    "/en/city/ca/manitoba/winnipeg/current"
   ],
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/city/ca/alberta/calgary/current"
   ],
   [
    "observe",
    "/en/city/ca/alberta/calgary/current"
   ]
  ],
  "answer": "Warmest to coldest right now: Toronto 18°C (Clear), Winnipeg 17°C (Light rain), Halifax 15°C (Mostly cloudy), Charlottetown 12°C (Clear), Calgary 6°C (Mostly cloudy).",
  "sql": []
 },
 18: {
  "steps": [
   [
    "click",
    "/en/news"
   ],
   [
    "observe",
    "/en/news"
   ],
   [
    "click",
    "/en/news/nature"
   ],
   [
    "observe",
    "/en/news/nature"
   ],
   [
    "click",
    "/en/news/nature/habitats/once-you-see-it-you-cant-unsee-it-ontarios-worst-invasive-plant-is-back-phragmites"
   ],
   [
    "observe",
    "/en/news/nature/habitats/once-you-see-it-you-cant-unsee-it-ontarios-worst-invasive-plant-is-back-phragmites"
   ]
  ],
  "answer": "The exact headline is \"'Once you see it, you can't unsee it': The 'road-trip ruiner' plant is back\". It is filed under the Nature category, Habitats subcategory, and was written by Cheryl Santa Maria, Digital Journalist. The plant — invasive phragmites — is dubbed 'Ontario's worst invasive plant' by Agriculture and Agrifood Canada. Over 300 sightings have been reported this season. It is believed to have arrived in Canada from Europe on ships through ballast material or packing materials, and its seeds spread around southern Ontario by hitching rides on boats, bicycles, hiking boots and ATVs.",
  "sql": []
 },
 19: {
  "steps": [
   [
    "input",
    "/en"
   ],
   [
    "observe",
    "/en"
   ],
   [
    "click",
    "/en/school/ca/alberta/banff-community-high-school/current"
   ],
   [
    "observe",
    "/en/school/ca/alberta/banff-community-high-school/current"
   ],
   [
    "click",
    "/en/school/ca/alberta/banff-community-high-school/hourly"
   ],
   [
    "observe",
    "/en/school/ca/alberta/banff-community-high-school/hourly"
   ],
   [
    "click",
    "/en/school/ca/alberta/banff-community-high-school/7-days"
   ],
   [
    "observe",
    "/en/school/ca/alberta/banff-community-high-school/7-days"
   ]
  ],
  "answer": "At Banff Community High School right now it is 3°C and Clear. Monday, September 28 during school hours is mainly sunny with no precipitation in the forecast (10% PoP, 0 mm) — the morning drop-off at 9 AM will be -1°C, warming to a daytime high of 12°C, so dry outdoor recess. The rest of the school week does not stay dry: Tuesday, September 29 and Wednesday, September 30 both show the highest rain chance at 60%.",
  "sql": []
 }
}

WRONG_ANSWERS = {
 0: "Halifax looks warmest overall; the probability of precipitation there is 100% on Saturday and 90% on Sunday.",
 1: "Nakiska Ski Area: the first date fresh snow is expected is October 2, with about 5 cm falling and a daytime high of 12°C.",
 2: "Winnipegosis and Dauphin are under the same single alert, a Frost advisory, which expires Thursday at noon.",
 3: "Hurricane Otis is the only eastern Pacific hurricane with a lower central pressure at 900 mb, and its top winds were 400 km/h; Polo peaked Monday, Sept. 21 with winds of 300 km/h, and its pressure fell only 50 mb in 24 hours; the videos are 'Polo grows stronger' and 'Riding inside Polo', and the eye-footage piece was written by Matt Howes on Sep. 27, 2026.",
 4: "Vancouver is the warmest at 57°F with winds of 7 mph.",
 5: "Bob has 5 locations saved in total now, and the account page shows Whistler Blackcomb at 48°F.",
 6: "Cancún is the warmer of the two, with a December average high of 31°C.",
 7: "Rain starts at 3 PM and the showers clear by 8 PM; 3 hours of rain at a 40% peak; it only gets down to 10°C overnight during the rain; the dry stretch beforehand spans 15-25°C; Monday afternoon climbs back to 25°C; the highest rain chance later in the week is Wednesday, September 30 at 60% with 1-3 mm expected.",
 8: "You can view radar for 5 cities; only Quebec has more than one; Ottawa is warmer at 20°C; 12 alerts across Canada and Ontario has 3 active alerts.",
 9: "The headline is 'Harvest Moon 2026'; the Moon is fullest at 8:30 PM on Sunday the 27th; it is named after the wheat harvest; NASA calls it the Blue Moon and the Super Moon.",
 10: "The best day is Friday with a 60% chance of precipitation and a high of 25°C; the warmest day is Monday; 2 days show a chance above 20 percent.",
 11: "The playlist holds 40 videos; the longest is 'Fat Bear Week is here' at 1:27; the shortest runs 30 seconds; the Featured playlist's longest video runs longer.",
 12: "Alberta Beach is the warmest on Saturday at 9°C; Aspen Beach is the one expecting rain; the three Sunday outlooks all differ.",
 13: "The warmest daytime high is 6°C on September 27; the coldest overnight low is -1°C; the wettest day is October 5; the typical high is 5°C so only 1° warmer; no alert covers Baker Lake.",
 14: "I created the account and saved Toronto, Vancouver and Halifax.",
 15: "Manitoba has the most alerts; they are all rainfall warnings recommending people carry umbrellas; Nunavut has 1 alert expiring Monday noon.",
 16: "Prairie communities see their first frost in late October; the article is filed under Science; a hard freeze is 0°C for an hour; no frost advisories have been issued yet.",
 17: "Coldest to warmest: Calgary 6°C, Charlottetown 12°C, Halifax 15°C, Winnipeg 17°C, Toronto 18°C.",
 18: "The headline is 'Invasive plant warning'; it is filed under Weather > Forecasts and written by Scott Sutherland; dubbed 'Canada's worst weed' by Environment Canada; 50 sightings reported.",
 19: "Tomorrow will be rainy with a high of 4°C and snow expected during school hours; the rest of the school week stays dry."
}

START_PATHS = {"0": "/en", "1": "/en", "2": "/en", "3": "/en", "4": "/en", "5": "/en", "6": "/en", "7": "/en", "8": "/en", "9": "/en", "10": "/en", "11": "/en", "12": "/en", "13": "/en", "14": "/en", "15": "/en", "16": "/en", "17": "/en", "18": "/en", "19": "/en"}

# Synthetic controls updated for the coherent reviewed tasks.
SPECS[5]["answer"] += " Saved locations: Vancouver, Victoria, Kelowna and Whistler Blackcomb."
SPECS[11]["answer"] += " Both fit into five minutes: 4:50 combined. The shortest shows a bat receiving water during a heat wave."

SPECS[11]["steps"].append(["click", "/en/video/PfcTWOOE"])
