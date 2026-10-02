"""Frozen per-task fixture specs for the statista verifier tests.

URLs are on the review origin (the verifiers check same-origin against the
trajectory start URL, not the registered site port). Honest answers state
each figure next to its subject so the subject-bound checks pass. MUTATIONS
reproduces the writes the application performs. No LLM.
"""

BASE = "http://localhost:46095"

def _u(*paths):
    out = [BASE + "/"]
    for path in paths:
        out.append(BASE + path)
    return out


SPECS = {
    0: dict(
        urls=_u(
            "/statistics/256598/global-inflation-rate-compared-to-previous-year/",
            "/statistics/256598/global-inflation-rate-compared-to-previous-year/?chart=table",
            "/register",
            "/account/favorites",
        ),
        answer=("4.13 is 2025 exactly here. "
                "3.2 is 2031 exactly here. "
                "I saved the statistic to my favorites."),
    ),
    1: dict(
        urls=_u(
            "/statistics/272014/global-social-networks-ranked-by-number-of-users/",
            "/register",
            "/account/downloads",
        ),
        answer=("The top network is Facebook* with 3070 million monthly active users. "
                "I downloaded the statistic as a PNG. "
                "The file is listed in the account download history."),
    ),
    2: dict(
        urls=_u(
            "/statistics/268173/countries-with-the-largest-gross-domestic-product-gdp/",
            "/register",
            "/account/favorites",
        ),
        answer=("The top economy is the United States with 32.38 trillion. "
                "Germany has 5.45 trillion. "
                "The United States is larger by 26.93 trillion. "
                "I saved the statistic to favorites."),
    ),
    3: dict(
        urls=_u(
            "/login",
            "/statistics/267233/renewable-energy-capacity-worldwide-by-country/",
            "/account/favorites",
        ),
        answer=("China leads with 2258.02 gigawatts. "
                "I added the statistic to favorites."),
    ),
    4: dict(
        urls=_u("/pricing/", "/register", "/account"),
        answer=("The cheapest plan that includes premium statistics is the Starter Account at 199 USD per month. "
                "The Personal Account costs 649 USD per month. "
                "The Professional Account costs 2388 USD per year. "
                "Report previews are a Personal feature. "
                "The Professional Account includes full reports and API access. "
                "The free Basic Account includes free statistics. "
                "The account type is Basic. "
                "Member since September 26, 2026. "
                "The starting favorites count is 0. "
                "The starting downloads count is 0."),
    ),
    5: dict(
        urls=_u(
            "/study/206237/consumer-trends-2026/",
            "/study/123559/video-gaming-worldwide/",
        ),
        answer=("The Consumer Trends report has 37 pages, was released in 2025, and costs 595 USD. "
                "Its first chapters are Consumer sentiment, Consumer spending and cautious optimism, and How tariffs are shaping consumption. "
                "The video gaming report has 62 pages, was released in 2026, and costs 495 USD. "
                "The format is PPTX and PDF. "
                "The video gaming report's first chapter is Overview. "
                "The video gaming report is longer than the other report. "
                "The pricier report costs 100 USD more."),
    ),
    6: dict(
        urls=_u(
            "/outlook/",
            "/outlook/mobility-markets/",
            "/outlook/mmo/shared-mobility/ride-hailing/worldwide/",
            "/outlook/mmo/shared-mobility/car-rentals/worldwide/",
        ),
        answer=("Worldwide ride-hailing 2026 revenue is 188.60 billion. "
                "Ride-hailing market volume by 2030 is 229.98 billion. "
                "Ride-hailing users by 2030 number 2.34 billion. "
                "Ride-hailing average revenue per user is 96.95. "
                "China generates the most ride-hailing revenue at 66 billion in 2026. "
                "Car rentals 2026 revenue is 112.00 billion. "
                "Car rentals market volume by 2030 is 135.75 billion. "
                "Car rentals users by 2030 number 776.96 million. "
                "168.53 is the car average exactly here. "
                "Ride-hailing has the higher revenue in 2026. "
                "That comparison uses the projected sales figure only. "
                "Car rentals have the higher average revenue per user. "
                "34 is the United States car figure."),
    ),
    7: dict(
        urls=_u(
            "/register",
            "/statistics/276629/global-co2-emissions/",
            "/statistics/276629/global-co2-emissions/?chart=table",
            "/account/favorites",
        ),
        answer=("The most recent year 2025 shows 38.11 billion metric tons. "
                "I saved the statistic to favorites and it appears in the new account."),
    ),
    8: dict(
        urls=_u(
            "/statistics/501853/leading-esports-games-worldwide-total-prize-pool/",
            "/statistics/501853/leading-esports-games-worldwide-total-prize-pool/?chart=table",
        ),
        answer=("Counter-Strike 18.97 exactly here. "
                "Dota 16.47 exactly here. "
                "Fortnite 12.91 exactly here. "
                "Rocket 8.5 exactly here. "
                "Legends 5.28 exactly here. "
                "Apex 5.0 exactly here. "
                "The chart ranks 10 games. "
                "The survey period is 01/01/2025 to 31/12/2025. "
                "The region is Worldwide. "
                "The value label is Total prize pool in million U.S. dollars. "
                "The top prize pool is bigger by 2.5 million."),
    ),
    9: dict(
        urls=_u(
            "/statistics/256598/global-inflation-rate-compared-to-previous-year/?citation=APA",
            "/statistics/256598/global-inflation-rate-compared-to-previous-year/?citation=MLA",
            "/statistics/276629/global-co2-emissions/?citation=APA",
        ),
        answer=("APA: Statista Research Department. (2026). Average inflation rate worldwide from 1980 to 2031. "
                "Statista. https://www.statista.com/statistics/256598/global-inflation-rate-compared-to-previous-year/ "
                "MLA includes Aug 13, 2026 and the same URL. "
                "CO2 APA: Statista Research Department. (April 2026). Annual global emissions of carbon dioxide 1940-2025. "
                "Statista. https://www.statista.com/statistics/276629/global-co2-emissions/ "
                "The inflation survey period runs from 01/01/1980 to 31/12/2031. "
                "The region is Worldwide."),
    ),
    10: dict(
        urls=_u(
            "/topics/6077/tiktok/",
            "/statistics/1299829/tiktok-penetration-worldwide-by-country/",
        ),
        answer=("Key insights: global users 1.99bn and a brand value of 75.67bn USD. "
                "The average video duration is 42.7 seconds and the average engagement rate is 3.67 percent. "
                "The country with the most users is Indonesia. "
                "The most popular content creator is Khabane Lame. "
                "The report on the topic is titled TikTok. "
                "The topic page was published by Lionel Sujay Vailshery on Jun 10, 2026. "
                "The editor's pick was last updated Jun 12, 2026. "
                "Its survey period is 01/04/2026 to 30/04/2026. "
                "Its region is Worldwide. "
                "Its value label is Share of population."),
    ),
    11: dict(
        urls=_u(
            "/login",
            "/account/downloads",
            "/account/favorites",
            "/forecasts/1474143/global-ai-market-size/",
        ),
        answer=("Alice's account type is Personal. "
                "Her most recent download is Market size of AI worldwide 2020-2032 in PNG format. "
                "The download before that was the most popular social networks statistic in XLS format. "
                "Her download history lists 3 downloads. "
                "Her favorites page listed 5 statistics before the removal. "
                "After the removal the favorites count is 4. "
                "The value label is Market size of AI in billion U.S. dollars. "
                "I removed the statistic."),
    ),
    12: dict(
        urls=_u(
            "/statistics/578364/countries-with-most-instagram-users/",
            "/statistics/578364/countries-with-most-instagram-users/?chart=table",
        ),
        answer=("India has 480.55 million. "
                "The United States has 181.75 million. "
                "Brazil has 147.0 million. "
                "Indonesia has 107.6 million. "
                "Japan has 63.2 million. "
                "India's audience is larger by 298.8 million than the United States. "
                "The chart compares 20 countries. "
                "Above 60 million: 6 countries. "
                "The update date is Oct 21, 2025. "
                "The survey period is 01/01/2025 to 31/12/2025. "
                "The region is Worldwide. "
                "The value label is Audience in millions."),
    ),
    13: dict(
        urls=_u(
            "/serp?q=artificial+intelligence&content_type=Reports",
            "/study/50485/in-depth-report-artificial-intelligence/",
            "/login",
            "/account/favorites",
        ),
        answer=("The report has 295 pages and costs 1995 USD. "
                "It was released in September 2025. "
                "The first table of contents entry is Description. "
                "I saved the report to favorites."),
    ),
    14: dict(
        urls=_u(
            "/statistics/256626/inflation-rate-in-selected-global-regions/",
            "/statistics/256598/global-inflation-rate-compared-to-previous-year/",
        ),
        answer=("Sub-Saharan 12.48 exactly here. "
                "European 2.46 exactly here. "
                "5.07 times separates the two rates. "
                "The regional survey period is 01/01/2025 to 31/12/2025. "
                "The regional page was updated Apr 15, 2026. "
                "The value label is Inflation rate compared with the previous year. "
                "4.13 is 2025 exactly here. "
                "3.2 is 2031 exactly here. "
                "The worldwide survey period is 01/01/1980 to 31/12/2031. "
                "Compared with the regional statistic, the worldwide average was updated more recently."),
    ),
    15: dict(
        urls=_u(
            "/login",
            "/study/206237/consumer-trends-2026/",
            "/account/downloads",
            "/account/favorites",
        ),
        answer=("The Consumer Trends report has 37 pages, release year 2025, and the price is 595 USD. "
                "Her download history shows 6 downloads. "
                "The new download format is PDF. "
                "The statistic downloaded most recently before it is installed renewable energy capacity, format PPT. "
                "The report is already in her favorites."),
    ),
    16: dict(
        urls=_u(
            "/statistics/326017/weekly-crude-oil-prices/",
            "/statistics/326017/weekly-crude-oil-prices/?chart=table",
        ),
        answer=("Jul 21 Brent 91.47 exactly here. "
                "Jul 21 WTI 84.91 exactly here. "
                "Jul 21 OPEC 88.5 exactly here. "
                "Jul 14 Brent 85.21 exactly here. "
                "Jul 14 WTI 79.34 exactly here. "
                "Jul 14 OPEC 86.16 exactly here. "
                "Brent 6.26 exactly here. "
                "WTI 5.57 exactly here. "
                "OPEC 2.34 exactly here. "
                "Apr 28 Brent 104.53 exactly here. "
                "Apr 28 OPEC 109.74 exactly here. "
                "Apr 28 WTI 99.93 exactly here. "
                "The survey period is January 6, 2020 to July 21, 2026. "
                "The update date is July 2026."),
    ),
    17: dict(
        urls=_u(
            "/markets/",
            "/markets/424/internet/",
            "/statistics/1044012/us-digital-audience/",
            "/statistics/1314183/youtube-shorts-performance-worldwide/",
            "/statistics/272014/global-social-networks-ranked-by-number-of-users/",
        ),
        answer=("As of October 2025 the United States had 324 million internet users and 254 million social media users. "
                "There were 70 million more internet users than social media users. "
                "The survey period is 01/01/2025 to 31/12/2025. "
                "The update date is Mar 18, 2026. "
                "1.5 is Jun Shorts. 2.0 is Jul Shorts. "
                "The Shorts update date is Jul 26, 2023. "
                "The Shorts survey period is 01/06/2022 to 31/07/2023. "
                "The top network is Facebook* with 3070 million and second is WhatsApp with 3000 million."),
    ),
    18: dict(
        urls=_u(
            "/statistics/1294062/social-media-year-on-year-growth/",
            "/statistics/1294062/social-media-year-on-year-growth/?chart=table",
        ),
        answer=("Pinterest grew 67.3 percent. "
                "TikTok grew 20.0 percent. "
                "Reddit grew 17.2 percent. "
                "X/Twitter shrank 20.1 percent. "
                "Snapchat had the smallest positive growth at 0.06 percent. "
                "The chart compares 9 platforms. "
                "The three fastest in the table are Pinterest, then TikTok, then Reddit. "
                "The update date is Jun 22, 2026. "
                "The survey period is 01/04/2026 to 30/04/2026. "
                "The region is Worldwide. "
                "The value label is Growth."),
    ),
    19: dict(
        urls=_u(
            "/statistics/379046/worldwide-retail-e-commerce-sales/",
            "/pricing/",
            "/statistics/439576/online-shopper-conversion-rate-worldwide/",
        ),
        answer=("You need a paid Statista Account. "
                "A Starter Account or higher is required to see the exact figures. "
                "The retail e-commerce page shows the update December 2025 and the region Worldwide. "
                "The Starter, Personal, and Professional accounts include premium statistics. "
                "The free Basic Account includes free statistics and does not include premium statistics. "
                "The cheapest paid plan is the Starter Account at 199 USD per month. "
                "The conversion statistic for Switzerland in Q2 '26 is 2.4 percent. "
                "The conversion statistic was updated Aug 6, 2026."),
    ),
    20: dict(
        urls=_u(
            "/login",
            "/topics/3104/artificial-intelligence-ai-worldwide/",
            "/forecasts/1474143/global-ai-market-size/",
            "/account/favorites",
        ),
        answer=("617.62 is the global market. "
                "63 is the generative market. "
                "I saved the editor's pick to favorites."),
    ),
    21: dict(
        urls=_u(
            "/study/123559/video-gaming-worldwide/",
            "/study/206237/consumer-trends-2026/",
            "/contact/",
        ),
        answer=("The video gaming report costs 495 USD, has 62 pages, and was released in 2026. "
                "Overview is a gaming chapter. "
                "The Consumer Trends report costs 595 USD. "
                "Thank you — your inquiry has been received."),
    ),
    22: dict(
        urls=_u(
            "/recent/statistics/",
            "/statistics/256598/global-inflation-rate-compared-to-previous-year/",
            "/statistics/276629/global-co2-emissions/",
        ),
        answer=("Inflation was updated Aug 13, 2026. "
                "Inflation covers Worldwide. "
                "Carbon dioxide was updated April 2026. "
                "Carbon dioxide covers Worldwide. "
                "Inflation was refreshed more recently."),
    ),
}

WRONG_ANSWERS = {
    0: "The 2025 average world inflation rate is 3.2 percent. The 2031 forecast value is 4.13 percent. I saved the statistic to my favorites.",
    1: "The top network is WhatsApp with 3000 million monthly active users. I downloaded the statistic as a PDF.",
    2: "The top economy is China with 20.85 trillion. Germany has 4.50 trillion. China is larger by 16.35 trillion.",
    3: "The United States leads with 467.92 gigawatts. I added the statistic to favorites.",
    4: "The cheapest premium plan is the Personal Account at 649 USD. The Professional Account costs 1199 per year. Member since January 1, 2020. The starting favorites count is 2.",
    5: "The Consumer Trends report has 45 pages, was released in 2026, and costs 495 USD. The video gaming report has 51 pages.",
    6: "Ride-hailing 2026 revenue is 112.00 billion. Car rentals 2026 revenue is 188.60 billion. China leads car rentals.",
    7: "The most recent year 2024 shows 37.78 billion metric tons. I saved the statistic to favorites.",
    8: "Dota 2 has a prize pool of 18.97 million. Counter-Strike 2 has 16.47 million. The chart ranks 10 games.",
    9: "The publisher is the IMF and the survey runs from 2000 to 2025.",
    10: "TikTok has 2.50bn users and a brand value of 100bn USD. The report on the topic is titled Digital Trends.",
    11: "Alice's most recent download is nominal GDP in XLS format. It was not removed from her favorites. Her history lists 1 download.",
    12: "The United States has 480.55 million. India has 181.75 million. Above 60 million: 3 countries. The chart compares 20 countries.",
    13: "The report has 250 pages and costs 2388 USD. It was released in March 2026. The first entry is Overview.",
    14: "The European Union had the highest rate at 12.48 percent. Sub-Saharan Africa was 2.46 percent. The highest is 5.07 times the European Union rate.",
    15: "The download format is XLS. The prior statistic is nominal GDP as PNG. Her history shows 2 downloads.",
    16: "For the week Jul 14 the Brent price was 91.47, the WTI price was 84.91, and the OPEC basket price was 88.5.",
    17: "The United States had 254 million internet users and 324 million social media users. YouTube Shorts usage was 2.0 billion in Jun '22 and 1.5 billion in Jul' 23.",
    18: "TikTok grew 67.3 percent. Pinterest grew 20.0 percent. Facebook shrank 20.1 percent. The chart compares 9 platforms.",
    19: "Only a Professional Account can see the exact figures. The Basic Account includes premium statistics. Switzerland in Q2 '25 is 2.4 percent.",
    20: "The global AI market size is 63bn USD. The generative AI market size is 617.62bn USD. I saved the editor's pick to favorites.",
    21: "The video gaming report costs 995 USD. I sent an inquiry as Dana Smith. The site said the form was rejected.",
    22: "Inflation was updated April 2026. Carbon dioxide was updated Aug 13, 2026. Carbon dioxide was refreshed more recently.",
}

# Complete answers with the right digits attached to the wrong subject.
# A loose substring check would pass these.
SWAP_ANSWERS = {
    0: WRONG_ANSWERS[0],
    2: "The top economy is the United States with 5.45 trillion. Germany has 32.38 trillion. Germany is larger by 26.93 trillion. I saved the statistic to favorites.",
    8: "Counter-Strike 2 has a prize pool of 16.47 million. Dota 2 has 18.97 million. Fortnite has 12.91 million. Rocket League has 8.5 million. League of Legends has 5.28 million. Apex Legends has 5.0 million. The chart ranks 10 games. The survey period is 01/01/2025 to 31/12/2025. The region is Worldwide. The value label is Total prize pool in million U.S. dollars. The top prize pool is bigger by 2.5 million.",
    12: "India has 181.75 million. The United States has 480.55 million. Brazil has 147.0 million. Indonesia has 107.6 million. Japan has 63.2 million. India's audience is larger by 298.8 million than the United States. The chart compares 20 countries. Above 60 million: 6 countries. The update date is Oct 21, 2025. The survey period is 01/01/2025 to 31/12/2025. The region is Worldwide. The value label is Audience in millions.",
    14: "Sub-Saharan Africa had the highest rate at 2.46 percent. The European Union rate was 12.48 percent. The highest is 5.07 times the European Union rate. The regional survey period is 01/01/2025 to 31/12/2025. The regional page was updated Apr 15, 2026. The value label is Inflation rate compared with the previous year. The worldwide average shows 2025 at 3.2 and 2031 at 4.13. The worldwide survey period is 01/01/1980 to 31/12/2031. Compared with the worldwide average, the regional statistic was updated more recently.",
    16: "For the week Jul 21 the Brent price was 84.91, the WTI price was 91.47, and the OPEC basket price was 88.5. For the week Jul 14 the Brent price was 85.21, the WTI price was 79.34, and the OPEC basket price was 86.16. Brent rose 6.26, WTI rose 5.57, and OPEC rose 2.34. For the earliest week Apr 28 the Brent price was 104.53, the OPEC basket price was 109.74, and the WTI price was 99.93. The survey period is January 6, 2020 to July 21, 2026. The update date is July 2026.",
    17: "As of October 2025 the United States had 254 million internet users and 324 million social media users. There were 70 million more internet users than social media users. The survey period is 01/01/2025 to 31/12/2025. The update date is Mar 18, 2026. YouTube Shorts usage was 2.0 billion in Jun '22 and 1.5 billion in Jul' 23. The Shorts update date is Jul 26, 2023. The Shorts survey period is 01/06/2022 to 31/07/2023. The top network is Facebook* with 3070 million and second is WhatsApp with 3000 million.",
    18: "Pinterest grew 20.0 percent. TikTok grew 67.3 percent. Reddit grew 17.2 percent. X/Twitter shrank 20.1 percent. Snapchat had the smallest positive growth at 0.06 percent. The chart compares 9 platforms. The three fastest in the table are Pinterest, then TikTok, then Reddit. The update date is Jun 22, 2026. The survey period is 01/04/2026 to 30/04/2026. The region is Worldwide. The value label is Growth.",
    20: WRONG_ANSWERS[20],
    22: "Inflation was updated April 2026. Inflation covers Worldwide. Carbon dioxide was updated Aug 13, 2026. Carbon dioxide covers Worldwide. Carbon dioxide was refreshed more recently.",
}

# The digit the old substring matcher would have accepted inside another number.
SUBSTRING_TRAPS = {
    12: ("India has 480.55 million. The United States has 181.75 million. "
         "Brazil has 147.0 million. Indonesia has 107.6 million. Japan has 63.2 million. "
         "India's audience is larger by 298.8 million than the United States. "
         "The chart compares 20 countries. Countries above 60 million are listed in the table. "
         "The update date is Oct 21, 2025. The survey period is 01/01/2025 to 31/12/2025. "
         "The region is Worldwide. The value label is Audience in millions."),
    18: ("Pinterest grew 67.3 percent. TikTok grew 20.0 percent. Reddit grew 17.2 percent. "
         "X/Twitter shrank 20.1 percent. Snapchat had the smallest positive growth at 0.06 percent. "
         "The chart compares platforms. The three fastest in the table are Pinterest, then TikTok, then Reddit. "
         "The update date is Jun 22, 2026. The survey period is 01/04/2026 to 30/04/2026. "
         "The region is Worldwide. The value label is Growth."),
}

_BCRYPT = "$2b$12$mTNQa9oqZyOoIJBpKN.0p.LVaApMSu9gZnYufEZrciM5QgBN7EM7u"

MUTATIONS = {
    0: [
        "INSERT INTO users (id, email, username, display_name, password_hash, account_type, company, created_at) "
        f"VALUES (5, 'review.agent0@test.com', 'review_agent0', 'Review_Agent0', '{_BCRYPT}', 'Basic', '', '2026-09-26 12:00:00')",
        "INSERT INTO favorites (id, user_id, stat_id, report_id, created_at) "
        "VALUES (16, 5, 256598, NULL, '2026-09-26 12:00:00')",
    ],
    1: [
        "INSERT INTO users (id, email, username, display_name, password_hash, account_type, company, created_at) "
        f"VALUES (5, 'review.agent1@test.com', 'review_agent1', 'Review_Agent1', '{_BCRYPT}', 'Basic', '', '2026-09-26 12:00:00')",
        "INSERT INTO download_events (id, user_id, stat_id, report_id, fmt, created_at) "
        "VALUES (13, 5, 272014, NULL, 'png', '2026-09-26 12:00:00')",
    ],
    2: [
        "INSERT INTO users (id, email, username, display_name, password_hash, account_type, company, created_at) "
        f"VALUES (5, 'review.agent2@test.com', 'review_agent2', 'Review_Agent2', '{_BCRYPT}', 'Basic', '', '2026-09-26 12:00:00')",
        "INSERT INTO favorites (id, user_id, stat_id, report_id, created_at) "
        "VALUES (16, 5, 268173, NULL, '2026-09-26 12:00:00')",
    ],
    3: [
        "INSERT INTO favorites (id, user_id, stat_id, report_id, created_at) "
        "VALUES (16, 2, 267233, NULL, '2026-09-26 12:00:00')",
    ],
    4: [
        "INSERT INTO users (id, email, username, display_name, password_hash, account_type, company, created_at) "
        f"VALUES (5, 'frank.miller@test.com', 'frank_m', 'Frank_M', '{_BCRYPT}', 'Basic', '', '2026-09-26 12:00:00')",
    ],
    7: [
        "INSERT INTO users (id, email, username, display_name, password_hash, account_type, company, created_at) "
        f"VALUES (5, 'casey.r@test.com', 'casey_r', 'Casey_R', '{_BCRYPT}', 'Basic', '', '2026-09-26 12:00:00')",
        "INSERT INTO favorites (id, user_id, stat_id, report_id, created_at) "
        "VALUES (16, 5, 276629, NULL, '2026-09-26 12:00:00')",
    ],
    11: [
        "DELETE FROM favorites WHERE user_id = 1 AND stat_id = 1474143",
    ],
    13: [
        "INSERT INTO favorites (id, user_id, stat_id, report_id, created_at) "
        "VALUES (16, 3, NULL, 50485, '2026-09-26 12:00:00')",
    ],
    15: [
        "INSERT INTO download_events (id, user_id, stat_id, report_id, fmt, created_at) "
        "VALUES (13, 3, NULL, 206237, 'pdf', '2026-09-26 12:00:00')",
    ],
    20: [
        "INSERT INTO favorites (id, user_id, stat_id, report_id, created_at) "
        "VALUES (16, 4, 1474143, NULL, '2026-09-26 12:00:00')",
    ],
    21: [
        "INSERT INTO inquiries (id, name, email, message, created_at) VALUES "
        "(1, 'Dana White', 'dana.white@example.com', "
        "'Asking about volume licensing for the video gaming report.', "
        "'2026-09-26 12:00:00')",
    ],
}


# Current browser regression fixtures (synthetic unit-test reconstructions, not new browser evidence).
SPECS = {0: {'answer': 'The worldwide inflation rate for 2025 is 4.13%. The forecast for 2031 is 3.2%. Saved the '
               'statistic to Bob’s favorites.',
     'urls': ['http://localhost:46095/',
              'http://localhost:46095/login',
              'http://localhost:46095/account',
              'http://localhost:46095/serp?q=global+inflation+rate+compared+to+previous+year',
              'http://localhost:46095/statistics/256598/global-inflation-rate-compared-to-previous-year/',
              'http://localhost:46095/statistics/256598/global-inflation-rate-compared-to-previous-year/?chart=table',
              'http://localhost:46095/account/favorites']},
 1: {'answer': 'The top network is Facebook* with 3070 million monthly active users. I downloaded the statistic '
               'as a PNG. The file is listed in the account download history.',
     'urls': ['http://localhost:46095/',
              'http://localhost:46095/login',
              'http://localhost:46095/account',
              'http://localhost:46095/serp?q=global+social+networks+ranked+by+number+of+users',
              'http://localhost:46095/statistics/272014/global-social-networks-ranked-by-number-of-users/',
              'http://localhost:46095/statistics/272014/global-social-networks-ranked-by-number-of-users/?chart=table',
              'http://localhost:46095/account/downloads']},
 2: {'answer': 'The top economy is the United States with 32.38 trillion. Germany has 5.45 trillion. The United '
               'States is larger by 26.93 trillion. I saved the statistic to favorites.',
     'urls': ['http://localhost:46095/',
              'http://localhost:46095/login',
              'http://localhost:46095/account',
              'http://localhost:46095/serp?q=nominal+GDP',
              'http://localhost:46095/statistics/268173/countries-with-the-largest-gross-domestic-product-gdp/',
              'http://localhost:46095/statistics/268173/countries-with-the-largest-gross-domestic-product-gdp/?chart=table',
              'http://localhost:46095/account/favorites']},
 3: {'answer': 'China leads with 2258.02 gigawatts. I added the statistic to favorites.',
     'urls': ['http://localhost:46095/',
              'http://localhost:46095/login',
              'http://localhost:46095/account',
              'http://localhost:46095/serp?q=renewable+energy+capacity+worldwide+by+country',
              'http://localhost:46095/statistics/267233/renewable-energy-capacity-worldwide-by-country/',
              'http://localhost:46095/statistics/267233/renewable-energy-capacity-worldwide-by-country/?chart=table',
              'http://localhost:46095/account/favorites']},
 4: {'answer': 'The cheapest plan that includes premium statistics is the Starter Account at 199 USD per month. '
               'The Personal Account costs 649 USD per month. The Professional Account costs 2388 USD per year. '
               'Report previews are a Personal feature. The Professional Account includes full reports and API '
               'access. The free Basic Account includes free statistics. The account type is Basic. Member since '
               'September 26, 2026. The starting favorites count is 0. The starting downloads count is 0.',
     'urls': ['http://localhost:46095/',
              'http://localhost:46095/pricing/',
              'http://localhost:46095/register',
              'http://localhost:46095/account']},
 5: {'answer': 'The Consumer Trends report has 37 pages, was released in 2025, and costs 595 USD. Its first '
               'chapters are Consumer sentiment, Consumer spending and cautious optimism, and How tariffs are '
               'shaping consumption. The video gaming report has 62 pages, was released in 2026, and costs 495 '
               "USD. The format is PPTX and PDF. The video gaming report's first chapter is Overview. The video "
               'gaming report is longer than the other report. The pricier report costs 100 USD more.',
     'urls': ['http://localhost:46095/',
              'http://localhost:46095/serp?q=consumer+trends+2026',
              'http://localhost:46095/study/206237/consumer-trends-2026/',
              'http://localhost:46095/serp?q=video+gaming+worldwide',
              'http://localhost:46095/study/123559/video-gaming-worldwide/']},
 6: {'answer': 'Worldwide ride-hailing 2026 revenue is 188.60 billion. Ride-hailing market volume by 2030 is '
               '229.98 billion. Ride-hailing users by 2030 number 2.34 billion. Ride-hailing average revenue per '
               'user is 96.95. China generates the most ride-hailing revenue at 66 billion in 2026. Car rentals '
               '2026 revenue is 112.00 billion. Car rentals market volume by 2030 is 135.75 billion. Car rentals '
               'users by 2030 number 776.96 million. Car rentals average revenue per user is $168.53. '
               'Ride-hailing has the higher revenue in 2026. That comparison uses the projected sales figure '
               'only. Car rentals have the higher average revenue per user. The United States generates the most '
               'car rental revenue at $34 billion in 2026.',
     'urls': ['http://localhost:46095/',
              'http://localhost:46095/outlook/',
              'http://localhost:46095/outlook/mobility-markets/',
              'http://localhost:46095/outlook/mmo/shared-mobility/ride-hailing/worldwide/',
              'http://localhost:46095/outlook/mmo/shared-mobility/car-rentals/worldwide/']},
 7: {'answer': 'The most recent year 2025 shows 38.11 billion metric tons. I saved the statistic to favorites and '
               'it appears in the new account.',
     'urls': ['http://localhost:46095/',
              'http://localhost:46095/register',
              'http://localhost:46095/account',
              'http://localhost:46095/serp?q=global+co2+emissions',
              'http://localhost:46095/statistics/276629/global-co2-emissions/',
              'http://localhost:46095/statistics/276629/global-co2-emissions/?chart=table',
              'http://localhost:46095/account/favorites']},
 8: {'answer': 'Counter-Strike 18.97 exactly here. Dota 16.47 exactly here. Fortnite 12.91 exactly here. Rocket '
               '8.5 exactly here. Legends 5.28 exactly here. Apex 5.0 exactly here. The chart ranks 10 games. The '
               'survey period is 01/01/2025 to 31/12/2025. The region is Worldwide. The value label is Total '
               'prize pool in million U.S. dollars. The top prize pool is bigger by 2.5 million. APA citation: '
               'Statista Research Department. (2026). Leading eSports games worldwide in 2025, by cumulative '
               'tournament prize pool (in million U.S. dollars). Statista. '
               'https://www.statista.com/statistics/501853/leading-esports-games-worldwide-total-prize-pool/',
     'urls': ['http://localhost:46095/',
              'http://localhost:46095/serp?q=leading+esports+games+worldwide+total+prize+pool',
              'http://localhost:46095/statistics/501853/leading-esports-games-worldwide-total-prize-pool/',
              'http://localhost:46095/statistics/501853/leading-esports-games-worldwide-total-prize-pool/?chart=table',
              'http://localhost:46095/statistics/501853/leading-esports-games-worldwide-total-prize-pool/?citation=APA']},
 9: {'answer': 'Inflation APA: Statista Research Department. (2026). Average inflation rate worldwide from 1980 '
               'to 2031. Statista. '
               'https://www.statista.com/statistics/256598/global-inflation-rate-compared-to-previous-year/\n'
               'Inflation MLA: Statista Research Department. "Average inflation rate worldwide from 1980 to '
               '2031." Statista, Aug 13, 2026, '
               'https://www.statista.com/statistics/256598/global-inflation-rate-compared-to-previous-year/.\n'
               'CO2 APA: Statista Research Department. (April 2026). Annual global emissions of carbon dioxide '
               '1940-2025. Statista. https://www.statista.com/statistics/276629/global-co2-emissions/\n'
               'The inflation statistic covers Worldwide, survey period January 1, 1980 to December 31, 2031.',
     'urls': ['http://localhost:46095/',
              'http://localhost:46095/serp?q=global+inflation+rate+compared+to+previous+year',
              'http://localhost:46095/statistics/256598/global-inflation-rate-compared-to-previous-year/',
              'http://localhost:46095/statistics/256598/global-inflation-rate-compared-to-previous-year/?citation=APA',
              'http://localhost:46095/statistics/256598/global-inflation-rate-compared-to-previous-year/?citation=MLA&chart=line',
              'http://localhost:46095/serp?q=global+co2+emissions',
              'http://localhost:46095/statistics/276629/global-co2-emissions/',
              'http://localhost:46095/statistics/276629/global-co2-emissions/?citation=APA']},
 10: {'answer': 'Key insights: global users 1.99bn and a brand value of 75.67bn USD. The average video duration '
                'is 42.7 seconds and the average engagement rate is 3.67 percent. The country with the most users '
                'is Indonesia. The most popular content creator is Khabane Lame. The report on the topic is '
                'titled TikTok. The topic page was published by Lionel Sujay Vailshery on Jun 10, 2026. The '
                "editor's pick was last updated Jun 12, 2026. Its survey period is 01/04/2026 to 30/04/2026. Its "
                'region is Worldwide. Its value label is Share of population.',
      'urls': ['http://localhost:46095/',
               'http://localhost:46095/serp?q=TikTok',
               'http://localhost:46095/serp?q=TikTok&content_type=Topics',
               'http://localhost:46095/topics/6077/tiktok/',
               'http://localhost:46095/statistics/1299829/tiktok-penetration-worldwide-by-country/']},
 11: {'answer': "Alice's account type is Personal. Her most recent download is Market size of AI worldwide "
                '2020-2032 in PNG format. The download before that was the most popular social networks statistic '
                'in XLS format. Her download history lists 3 downloads. Her favorites page listed 5 statistics '
                'before the removal. After the removal the favorites count is 4. The value label is Market size '
                'of AI in billion U.S. dollars. I removed the statistic.',
      'urls': ['http://localhost:46095/',
               'http://localhost:46095/login',
               'http://localhost:46095/account',
               'http://localhost:46095/account/downloads',
               'http://localhost:46095/account/favorites',
               'http://localhost:46095/forecasts/1474143/global-ai-market-size/',
               'http://localhost:46095/forecasts/1474143/global-ai-market-size/?chart=line']},
 12: {'answer': 'India has 480.55 million. The United States has 181.75 million. Brazil has 147.0 million. '
                "Indonesia has 107.6 million. Japan has 63.2 million. India's audience is larger by 298.8 million "
                'than the United States. The chart compares 20 countries. Above 60 million: 6 countries. The '
                'update date is Oct 21, 2025. The survey period is 01/01/2025 to 31/12/2025. The region is '
                'Worldwide. The value label is Audience in millions. APA citation: Statista Research Department. '
                '(2025). Leading countries based on Instagram audience size as of October 2025 (in millions). '
                'Statista. https://www.statista.com/statistics/578364/countries-with-most-instagram-users/',
      'urls': ['http://localhost:46095/',
               'http://localhost:46095/serp?q=countries+with+most+instagram+users',
               'http://localhost:46095/statistics/578364/countries-with-most-instagram-users/',
               'http://localhost:46095/statistics/578364/countries-with-most-instagram-users/?chart=table',
               'http://localhost:46095/statistics/578364/countries-with-most-instagram-users/?citation=APA']},
 13: {'answer': 'The report has 295 pages and costs 1995 USD. It was released in September 2025. The first table '
                'of contents entry is Description. I saved the report to favorites.',
      'urls': ['http://localhost:46095/',
               'http://localhost:46095/login',
               'http://localhost:46095/account',
               'http://localhost:46095/serp?q=artificial+intelligence',
               'http://localhost:46095/serp?q=artificial%20intelligence&content_type=Reports',
               'http://localhost:46095/study/50485/in-depth-report-artificial-intelligence/',
               'http://localhost:46095/account/favorites']},
 14: {'answer': 'Sub-Saharan 12.48 exactly here. European 2.46 exactly here. 5.07 times separates the two rates. '
                'The regional survey period is 01/01/2025 to 31/12/2025. The regional page was updated Apr 15, '
                '2026. The value label is Inflation rate compared with the previous year. 4.13 is 2025 exactly '
                'here. 3.2 is 2031 exactly here. The worldwide survey period is 01/01/1980 to 31/12/2031. '
                'Compared with the regional statistic, the worldwide average was updated more recently.',
      'urls': ['http://localhost:46095/',
               'http://localhost:46095/serp?q=inflation+rate+in+selected+global+regions',
               'http://localhost:46095/statistics/256626/inflation-rate-in-selected-global-regions/',
               'http://localhost:46095/statistics/256626/inflation-rate-in-selected-global-regions/?chart=table',
               'http://localhost:46095/serp?q=global+inflation+rate+compared+to+previous+year',
               'http://localhost:46095/statistics/256598/global-inflation-rate-compared-to-previous-year/',
               'http://localhost:46095/statistics/256598/global-inflation-rate-compared-to-previous-year/?chart=table']},
 15: {'answer': 'Consumer Trends 2026 has 37 pages, release year 2025, price $595 USD. Its first chapters are '
                'Consumer sentiment, Consumer spending and cautious optimism, and How tariffs are shaping '
                'consumption. Downloaded as PDF; Carol now has 6 downloads.',
      'urls': ['http://localhost:46095/',
               'http://localhost:46095/login',
               'http://localhost:46095/account',
               'http://localhost:46095/serp?q=consumer+trends+2026',
               'http://localhost:46095/study/206237/consumer-trends-2026/',
               'http://localhost:46095/account/downloads']},
 16: {'answer': 'Jul 21 Brent 91.47 exactly here. Jul 21 WTI 84.91 exactly here. Jul 21 OPEC 88.5 exactly here. '
                'Jul 14 Brent 85.21 exactly here. Jul 14 WTI 79.34 exactly here. Jul 14 OPEC 86.16 exactly here. '
                'Brent 6.26 exactly here. WTI 5.57 exactly here. OPEC 2.34 exactly here. Apr 28 Brent 104.53 '
                'exactly here. Apr 28 OPEC 109.74 exactly here. Apr 28 WTI 99.93 exactly here. The survey period '
                'is January 6, 2020 to July 21, 2026. The update date is July 2026.',
      'urls': ['http://localhost:46095/',
               'http://localhost:46095/serp?q=weekly+crude+oil+prices',
               'http://localhost:46095/statistics/326017/weekly-crude-oil-prices/',
               'http://localhost:46095/statistics/326017/weekly-crude-oil-prices/?chart=table']},
 17: {'answer': 'The U.S. had 324 million internet users and 254 million social media users in October 2025: 70 '
                'million more internet users. Survey period January 1, 2025 to December 31, 2025; updated March '
                '18, 2026. Facebook leads globally with 3,070 million users; WhatsApp has 3,000 million users and '
                'Instagram also has 3,000 million users, tied for second. Both trail Facebook by 70 million. The '
                'global statistic has survey period January 1, 2025 to December 31, 2025 and was updated March '
                '11, 2026. These platform totals cover Worldwide and cannot be treated as U.S. audiences.',
      'urls': ['http://localhost:46095/',
               'http://localhost:46095/markets/',
               'http://localhost:46095/markets/424/internet/',
               'http://localhost:46095/statistics/1044012/us-digital-audience/',
               'http://localhost:46095/serp?q=global+social+networks+ranked+by+number+of+users',
               'http://localhost:46095/statistics/272014/global-social-networks-ranked-by-number-of-users/',
               'http://localhost:46095/statistics/272014/global-social-networks-ranked-by-number-of-users/?chart=table']},
 18: {'answer': 'Pinterest grew 67.3 percent. TikTok grew 20.0 percent. Reddit grew 17.2 percent. X/Twitter '
                'shrank 20.1 percent. Snapchat had the smallest positive growth at 0.06 percent. The chart '
                'compares 9 platforms. The three fastest in the table are Pinterest, then TikTok, then Reddit. '
                'The update date is Jun 22, 2026. The survey period is 01/04/2026 to 30/04/2026. The region is '
                'Worldwide. The value label is Growth. APA citation: Statista Research Department. (2026). '
                'Year-on-year audience growth of selected social media platforms worldwide as of April 2026. '
                'Statista. https://www.statista.com/statistics/1294062/social-media-year-on-year-growth/',
      'urls': ['http://localhost:46095/',
               'http://localhost:46095/serp?q=social+media+year+on+year+growth',
               'http://localhost:46095/statistics/1294062/social-media-year-on-year-growth/',
               'http://localhost:46095/statistics/1294062/social-media-year-on-year-growth/?chart=table',
               'http://localhost:46095/statistics/1294062/social-media-year-on-year-growth/?citation=APA']},
 19: {'answer': 'You need a paid Statista Account. A Starter Account or higher is required to see the exact '
                'figures. The retail e-commerce page shows the update December 2025 and the region Worldwide. The '
                'Starter, Personal, and Professional accounts include premium statistics. The free Basic Account '
                'includes free statistics and does not include premium statistics. The cheapest paid plan is the '
                "Starter Account at 199 USD per month. The conversion statistic for Switzerland in Q2 '26 is 2.4 "
                'percent. The conversion statistic was updated Aug 6, 2026.',
      'urls': ['http://localhost:46095/',
               'http://localhost:46095/serp?q=worldwide+retail+e+commerce+sales',
               'http://localhost:46095/statistics/379046/worldwide-retail-e-commerce-sales/',
               'http://localhost:46095/pricing/',
               'http://localhost:46095/serp?q=online+shopper+conversion+rate+worldwide',
               'http://localhost:46095/statistics/439576/online-shopper-conversion-rate-worldwide/',
               'http://localhost:46095/statistics/439576/online-shopper-conversion-rate-worldwide/?chart=table']},
 20: {'answer': "617.62 is the global market. 63 is the generative market. I saved the editor's pick to "
                'favorites.',
      'urls': ['http://localhost:46095/',
               'http://localhost:46095/login',
               'http://localhost:46095/account',
               'http://localhost:46095/serp?q=artificial+intelligence+worldwide',
               'http://localhost:46095/serp?q=artificial%20intelligence%20worldwide&content_type=Topics',
               'http://localhost:46095/topics/3104/artificial-intelligence-ai-worldwide/',
               'http://localhost:46095/forecasts/1474143/global-ai-market-size/',
               'http://localhost:46095/forecasts/1474143/global-ai-market-size/?chart=line',
               'http://localhost:46095/account/favorites']},
 21: {'answer': 'The video gaming report costs $495 USD, has 62 pages, was released in 2026, and starts with '
                'Overview. Inquiry sent as Dana White, dana.white@example.com, about volume licensing. The site '
                'confirms that the message was sent.',
      'urls': ['http://localhost:46095/',
               'http://localhost:46095/serp?q=video+gaming+worldwide',
               'http://localhost:46095/study/123559/video-gaming-worldwide/',
               'http://localhost:46095/contact/']},
 22: {'answer': 'Inflation was updated Aug 13, 2026. Inflation covers Worldwide. Carbon dioxide was updated April '
                '2026. Carbon dioxide covers Worldwide. Inflation was refreshed more recently.',
      'urls': ['http://localhost:46095/',
               'http://localhost:46095/recent/statistics/',
               'http://localhost:46095/serp?q=global+inflation+rate+compared+to+previous+year',
               'http://localhost:46095/statistics/256598/global-inflation-rate-compared-to-previous-year/',
               'http://localhost:46095/serp?q=global+co2+emissions',
               'http://localhost:46095/statistics/276629/global-co2-emissions/']}}
MUTATIONS = {0: ['INSERT INTO "favorites" ("id", "user_id", "stat_id", "report_id", "created_at") VALUES (16, 2, 256598, '
     "NULL, '2026-09-26 12:00:00.000000');"],
 1: ['INSERT INTO "download_events" ("id", "user_id", "stat_id", "report_id", "fmt", "created_at") VALUES (13, 2, '
     "272014, NULL, 'png', '2026-09-26 12:00:00.000000');"],
 2: ['INSERT INTO "favorites" ("id", "user_id", "stat_id", "report_id", "created_at") VALUES (16, 2, 268173, '
     "NULL, '2026-09-26 12:00:00.000000');"],
 3: ['INSERT INTO "favorites" ("id", "user_id", "stat_id", "report_id", "created_at") VALUES (16, 2, 267233, '
     "NULL, '2026-09-26 12:00:00.000000');"],
 4: ['INSERT INTO "users" ("id", "email", "username", "display_name", "password_hash", "account_type", "company", '
     '"created_at") VALUES (5, \'frank.miller@test.com\', \'frank_m\', \'Frank Miller\', '
     "X'24326224313224795143516475634e4b687a593154372e39386442384f567454656f5a336f39334a4c49336c41544d456254674a3465545170416865', "
     "'Basic', '', '2026-09-26 12:00:00.000000');"],
 5: [],
 6: [],
 7: ['INSERT INTO "users" ("id", "email", "username", "display_name", "password_hash", "account_type", "company", '
     '"created_at") VALUES (5, \'casey.r@test.com\', \'casey_r\', \'Casey_R\', '
     "X'24326224313224446c6953487a43733347447458366e726a6f31524f4f3547764b32616a6a4b327556477768786a616f66743474664464374d456175', "
     "'Basic', '', '2026-09-26 12:00:00.000000');",
     'INSERT INTO "favorites" ("id", "user_id", "stat_id", "report_id", "created_at") VALUES (16, 5, 276629, '
     "NULL, '2026-09-26 12:00:00.000000');"],
 8: [],
 9: [],
 10: [],
 11: ['DELETE FROM "favorites" WHERE "id"=3;'],
 12: [],
 13: ['INSERT INTO "favorites" ("id", "user_id", "stat_id", "report_id", "created_at") VALUES (16, 3, NULL, '
      "50485, '2026-09-26 12:00:00.000000');"],
 14: [],
 15: ['INSERT INTO "download_events" ("id", "user_id", "stat_id", "report_id", "fmt", "created_at") VALUES (13, '
      "3, NULL, 206237, 'pdf', '2026-09-26 12:00:00.000000');"],
 16: [],
 17: [],
 18: [],
 19: [],
 20: ['INSERT INTO "favorites" ("id", "user_id", "stat_id", "report_id", "created_at") VALUES (16, 4, 1474143, '
      "NULL, '2026-09-26 12:00:00.000000');"],
 21: ['INSERT INTO "inquiries" ("id", "name", "email", "message", "created_at") VALUES (1, \'Dana White\', '
      "'dana.white@example.com', 'Please advise on volume licensing for the Video gaming worldwide report for our "
      "team.', '2026-09-26 12:00:00.000000');"],
 22: []}

MUTATIONS = {n: sql for n, sql in MUTATIONS.items() if sql}
