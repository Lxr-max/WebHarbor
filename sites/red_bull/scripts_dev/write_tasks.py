#!/usr/bin/env python3
"""Write sites/red_bull/tasks.jsonl (contributor 5-key rows)."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "tasks.jsonl"
WEB = "http://localhost:40133/"
UPSTREAM = "https://www.redbull.com/"

TASKS = [
    # 0 — events calendar + tabs + ticketed registration
    "I surf soft-boards and want to compete at the Red Bull Foam Wreckers stop on the Virginia Beach oceanfront this October. From the event calendar, open that stop, check its FAQs for the type of surfboard required and whether spectators need tickets, check the Schedule tab for when check-in runs, then register me as Casey Rider (casey.rider@example.com). Report the entry fee and my registration code, plus the venue of the other October Foam Wreckers stop in Rhode Island.",
    # 1 — registration-open scan + fee comparison + registration
    "Find every upcoming US event on the calendar whose card shows open registrations. List which of them charge an entry fee and which are free, with each fee amount. Then register me for the cheapest one that charges a fee as Sam Porter (sam.porter@example.com). Report that event's venue and date, and my registration code.",
    # 2 — calendar filters across three disciplines
    "I'm planning a motorsport autumn. From the event calendar: find the US motocross event in Iowa and report its venue and which era of dirt bikes it celebrates (from the description); find the German DTM round at the Nürburgring and report its dates, then the dates of the Hockenheimring round; find the esports event whose qualifiers are played on EA SPORTS FC 27 and report its full date range and the status badge on its card.",
    # 3 — event series tour stops
    "The Polignano a Mare cliff diving event is part of a world series. From the event calendar, open that event, follow its series link, and report the series' one-line description and every tour stop with its country. Then open the King of the Air event series page and report how many stops it lists. Finally report how many stops the Red Bull Foam Wreckers series has.",
    # 4 — FAQs + failed-then-valid free registration
    "I want to enter the Red Bull basketball free-throw event in Burbank this October. From the event calendar, open it and read its FAQs to learn how many teams can compete and what time participant check-in opens (Schedule tab). Then try to register with the email 'not-an-email' and no name, confirm the errors shown, and finally register correctly as Dana Kim (dana.k@example.com). Report my registration code and the entry fee.",
    # 5 — product comparison + sugarfree variants
    "I'm comparing Red Bull flavors. From the Energy Drinks catalog: open the Summer Edition and the Original, and report each one's caffeine and sugars per 8.4 fl oz can and every available size. Then list which Editions flavors also come in a sugarfree variant, open the Red Edition to confirm whether it has a sugarfree twin, and open the Amber Edition and the Peach Edition to report their caffeine and sugars. Finally tell me which product — Red Bull Zero or Red Bull Sugarfree — is sweetened with monk fruit extract.",
    # 6 — athlete filters + profiles + A-Z index
    "List every United Kingdom athlete on the Athletes page with their discipline, then open each UK athlete's profile and report each one's career start year. After that, use the A-Z index letter matching Terry Adams' last name to find him, and report his full discipline and nationality.",
    # 7 — films catalog: newest, filter, pagination
    "Browse the Films catalog and report the newest film's title, its one-line subheading and its runtime. Then filter films to Snowboarding, report how many are listed and open the first one to report its subheading. Also report how many Surfing films there are, and how many esports films. Finally go to page 2 of the full Films catalog and report the title of the first film shown there.",
    # 8 — shows + episode table
    "In the Shows catalog, find the series about winter-sport heroes, open it and report its season and episode counts and the titles of its first three episodes. Then filter shows to Snowboarding, report how many are listed, and open the first one to report its subheading and episode count. Then find 'No Contest' and report its discipline and episode count. Finally report the season and episode counts of Inside Pro Surfing, then open the second snowboarding show and report its title and episode count.",
    # 9 — stories: topic filters + facts
    "In Stories, filter to the Dance topic and open the article about the dancer who won the 2026 Red Bull Dance Your Style USA final: report where the final was held, the winner's age, and her home state. Then report how many stories the Games topic lists, open the GTA 6 facts story and report one surprising fact from its body. Finally open the UCI World Championships explainer and report one fact about the rainbow jersey, plus the title and topic of the newest story overall.",
    # 10 — shop filters + cart + checkout
    "Log in as Alice Johnson (alice.j@test.com, TestPass123!). In the Shop, filter to Oracle Red Bull Racing headwear, sort by price, open the cheapest item and report its title and price. Add it to the cart in any available size, set quantity to 2, then complete checkout with shipping to Alice Johnson, alice.j@test.com, 1 Main St, Seattle, 98101. Report the order number and total.",
    # 11 — shop product detail + cheapest overall + vendor count
    "In the Shop, open the Oracle Red Bull Racing Classic Hoodie and report its material composition, its price for size XS, and its product category. Then browse all products sorted by price, open the cheapest item in the whole shop and report its title, price and category. Also report how many products the headwear category lists, how many the Red Bull Rampage brand has, and how many bags there are.",
    # 12 — shop vendor browse + cart + removal
    "In the Shop, filter to the FC Red Bull Salzburg brand and report how many products are listed and the lowest price among them. Open the cheapest one, report its title and category, add it to the cart in any size, and report the cart subtotal. Then open the second-cheapest Salzburg product and add it too, report the new subtotal, and finally remove the first item and confirm the cart still contains the second.",
    # 13 — account: registration details + favorites management
    "Log in as Bob Chen (bob.c@test.com, TestPass123!). On his account page, report the registration code for the motocross event he is registered for, that event's date, and its ticket type. Then remove Bob's saved show from his favorites, and save the Iowa motocross event to his favorites instead. Report the event's venue. Finally open the story Bob has favorited and report its topic.",
    # 14 — favorites flow
    "Log in as Carol Davis (carol.d@test.com, TestPass123!). Report the event and film she has already saved as favorites. Then open the Iowa motocross event from the calendar and save it to favorites, and confirm it now appears on her account page. Also save the film about a snowboarding season seen through a pro's eyes to her favorites and report its runtime.",
    # 15 — past events by country
    "From the event calendar, list every already-finished German event this season with its venue and dates, then report which German city hosted the urban downhill mountain bike race and what its description says riders face. Also open the Sachsenring DTM round and report its dates, then open the ADAC MX Masters round at Fürstlich Drehna and report its dates and discipline, and open the drifting event and report its venue. Finally report how many German events the calendar lists in total and how many of them are still upcoming.",
    # 16 — US upcoming calendar + badges + fees
    "From the event calendar, filter to upcoming events in the United States and report how many are listed and the title and date of the earliest one. Then open the esports tournament played on EA SPORTS FC 27 and report its standfirst and registration fee. Also open the October surf event in Narragansett and report whether its card shows a 'Registrations open' badge and its venue. Finally open the basketball event in Burbank and report its venue and entry fee.",
    # 17 — Editions flavors + sizes + caffeine
    "From the Energy Drinks catalog, open the Amber, Yellow and Red Editions and report each one's flavor. Then report the largest can size the Original Red Bull Energy Drink comes in, the caffeine amount in every 8.4 fl oz can of the Peach Edition Sugarfree, every available size of the Red Bull Sugarfree flagship, and the flavor of the Summer Edition.",
    # 18 — cross-section: event -> related story
    "From the event calendar, open the Red Bull Dance Your Style USA national final and report its venue and date. Follow its related story and report where the final was held, who won it, and her age. Then find the world final event in the calendar and report its venue and date. Finally find the Red Bull BC One Cypher USA final and report its venue.",
    # 19 — athlete profile + story link
    "Find the supercross athlete Eli Tomac on the Athletes page (filter by his discipline), open his profile, and report his nationality, date of birth, and where he grew up racing (from his bio). Then find the US athlete who rides BMX Flatland and report his birthplace. Finally in Stories, open the article explaining the difference between supercross and motocross and report one difference stated in its body, and report how many Skateboarding-topic stories there are.",
]


def main() -> None:
    rows = []
    for i, ques in enumerate(TASKS):
        words = len(ques.split())
        assert words <= 100, f"task {i} too long: {words} words"
        rows.append({"web_name": "Red Bull", "id": f"Red Bull--{i}",
                     "ques": ques, "web": WEB, "upstream_url": UPSTREAM})
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                   encoding="utf-8")
    print(f"wrote {len(rows)} tasks; word counts:",
          [len(q.split()) for q in TASKS])


if __name__ == "__main__":
    main()
