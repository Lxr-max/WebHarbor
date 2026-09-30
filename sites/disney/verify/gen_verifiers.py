#!/usr/bin/env python3
"""gen_verifiers.py — emit verify_0.py .. verify_19.py for the disney
reviewer contract from the frozen walk ground truths.

Every ground truth below was transcribed from the reviewer's own
independent Playwright honest-path walks (per-task reset + fresh context,
webharbor-disney-review container, seed sha256 e995566b…), never from
tasks.jsonl. Known premise/navigation defects are pinned with explanatory
notes (see verify_lib.py's header): a fix that moves these truths must
re-freeze the affected verifiers.

Run: python3 gen_verifiers.py   (writes verify_<n>.py next to this file)
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent

HEADER = '''#!/usr/bin/env python3
"""Deterministic verifier for Disney--{n} (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.
{note}
Usage: python3 verify_{n}.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
{imports}
)

TASK_ID = "Disney--{n}"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
{nav}
    # -- answer ground truth --
{ans}

{db}
if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
'''

IMPORTS = [
    "check_answer_absent", "check_answer_any", "check_answer_count_at_least",
    "check_answer_number", "check_answer_number_absent", "check_answer_ordered",
    "check_answer_phrase", "check_answer_regex", "check_read_only",
    "check_only_tables_changed", "check_row_matches", "check_rows_added",
    "check_screenshots", "check_seed_contract",
    "check_trajectory_identity", "check_visited_all", "check_visited_any",
    "check_visited_path", "run_verifier",
]
IMPORT_BLOCK = ",\n".join("    " + i for i in sorted(set(IMPORTS)))


def emit(n, note, nav, ans, db):
    nav_txt = "\n".join(nav)
    ans_txt = "\n".join(ans)
    body = HEADER.format(n=n, note=note, imports=IMPORT_BLOCK,
                         nav=nav_txt, ans=ans_txt, db=db)
    (HERE / f"verify_{n}.py").write_text(body, encoding="utf-8")
    print(f"wrote verify_{n}.py ({len(body.splitlines())} lines)")


# ------------------------------------------------------------------ specs --
# nav: list of python lines. ans: list of python lines. db: final block.

def nav(*gates):
    return [f'    check_visited_path(judge, traj, "{name}", r"""{rx}"""),' for name, rx in gates]


def navany(name, pats):
    p = ", ".join(f'r"""{x}"""' for x in pats)
    return [f'    check_visited_any(judge, traj, "{name}", [{p}]),']


def num(name, value):
    return f'    check_answer_number(judge, answer, "{name}", {value!r})'


def phrase(name, value):
    v = value.replace('\\', '\\\\').replace('"', '\\"')
    return f'    check_answer_phrase(judge, answer, "{name}", "{v}")'


def anyph(name, values):
    vs = ", ".join('"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"' for v in values)
    return f'    check_answer_any(judge, answer, "{name}", [{vs}])'


def regex(name, pattern):
    return f'    check_answer_regex(judge, answer, "{name}", r"{pattern}")'


READ_ONLY_DB = """    check_read_only(judge, initial, after)
"""

SPEC = {}

# ---------------------------------------------------------------- T0
SPEC[0] = dict(
    note="",
    nav=nav(
        ("movies_streaming", r"/movies\?[^\" ]*status=streaming"),
        ("first_streaming_detail", r"/movies/avatar-the-way-of-water"),
        ("movies_coming_soon", r"/movies\?[^\" ]*status=coming_soon"),
        ("first_cs_detail", r"/movies/avengers-doomsday"),
        ("login", r"/login"),
        ("favorites", r"/favorites"),
    ),
    ans=[
        num("streaming_count", 6),
        phrase("first_title", "Avatar: The Way of Water"),
        phrase("rating", "PG-13"),
        phrase("runtime", "3h 12min"),
        num("coming_soon_count", 9),
        phrase("cs_release_date", "December 18, 2026"),
        num("alice_favorites_total", 4),
    ],
    db="""    check_only_tables_changed(judge, initial, after, {"favorites"})
    check_rows_added(judge, initial, after, "favorites", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites WHERE user_id=1 AND item_type='movie' AND item_key='avengers-doomsday'",
        (), "alice_faved_avengers_doomsday")
""",
)

# ---------------------------------------------------------------- T1
SPEC[1] = dict(
    note="",
    nav=nav(
        ("signup", r"/signup"),
        ("movies_coming_soon", r"/movies\?[^\" ]*status=coming_soon"),
        ("cs_animation", r"/movies\?[^\" ]*status=coming_soon[^\" ]*genre=Animation|/movies\?[^\" ]*genre=Animation[^\" ]*status=coming_soon"),
        ("first_detail", r"/movies/frozen-3"),
        ("login", r"/login"),
        ("favorites", r"/favorites"),
    ),
    ans=[
        num("cs_count", 9),
        num("cs_animation_count", 6),
        phrase("first_title", "Frozen 3"),
        phrase("release_date", "November 24, 2027"),
        phrase("rating", "Not Yet Rated"),
        num("moana_favorites_total", 1),
        phrase("fav_title", "Frozen 3"),
    ],
    db="""    check_only_tables_changed(judge, initial, after, {"users", "favorites"})
    check_rows_added(judge, initial, after, "users", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM users WHERE email='moana.fan@test.com' AND name='Moana Fan'",
        (), "moana_account")
    check_rows_added(judge, initial, after, "favorites", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites f JOIN users u ON f.user_id=u.id "
        "WHERE u.email='moana.fan@test.com' AND f.item_type='movie' AND f.item_key='frozen-3'",
        (), "moana_faved_frozen3")
""",
)

# ---------------------------------------------------------------- T2
SPEC[2] = dict(
    note="""    r2 note: the task now says "open the first result" for the
    release-date sort (the r1 wording "most recently released" was
    ambiguous); the anchor is unchanged — the top of the release sort is
    Star Wars: Starfighter (May 28, 2027, Not Yet Rated).
""",
    nav=nav(
        ("movies_star_search", r"/movies\?[^\" ]*q=star"),
        ("cs_scifi", r"/movies\?[^\" ]*status=coming_soon[^\" ]*genre=Science\+Fiction|/movies\?[^\" ]*genre=Science\+Fiction[^\" ]*status=coming_soon"),
        ("doomsday_detail", r"/movies/avengers-doomsday"),
        ("scifi_release_sort", r"/movies\?[^\" ]*genre=Science\+Fiction[^\" ]*sort=release|/movies\?[^\" ]*sort=release[^\" ]*genre=Science\+Fiction"),
        ("newest_detail", r"/movies/star-wars-starfighter"),
        ("scifi_title_sort", r"/movies\?[^\" ]*genre=Science\+Fiction[^\" ]*sort=title|/movies\?[^\" ]*sort=title[^\" ]*genre=Science\+Fiction"),
        ("first_scifi_detail", r"/movies/avatar-fire-and-ash"),
    ),
    ans=[
        num("star_count", 2),
        num("cs_scifi_count", 2),
        phrase("first_cs_scifi_date", "December 18, 2026"),
        phrase("newest_title", "Star Wars: Starfighter"),
        phrase("newest_rating", "Not Yet Rated"),
        phrase("newest_date", "May 28, 2027"),
        phrase("title_first", "Avatar: Fire and Ash"),
        phrase("title_first_rating", "PG-13"),
        anyph("cast_member", ["Sam Worthington", "Zoe Saldaña", "Sigourney Weaver",
                              "Stephen Lang", "Oona Chaplin", "Cliff Curtis",
                              "David Thewlis", "Giovanni Ribisi", "Kate Winslet"]),
    ],
    db=READ_ONLY_DB,
)

# ---------------------------------------------------------------- T3
SPEC[3] = dict(
    note="""    r2 note: the task now says "clear the search and the genre filter,
    open the newer DuckTales series" — the two same-titled shows (1987
    original / 2017 reboot) make "newer" deterministic: the 2017 reboot
    at /shows/ducktales (TV-Y7). The agent must clear the still-active
    Science Fiction genre filter to see the card.
""",
    nav=nav(
        ("shows_animation", r"/shows\?[^\" ]*genre=Animation"),
        ("shows_scifi", r"/shows\?[^\" ]*genre=Science\+Fiction"),
        ("shows_star_search", r"/shows\?[^\" ]*q=star"),
        ("first_star_detail", r"/shows/lego-star-wars-droid-tales"),
        ("shows_cleared", r"/shows\?[^\" ]*genre=&"),
    ) + navany("ducktales_detail", [r"/shows/ducktales$"]) + nav(
        ("bh6_detail", r"/shows/big-hero-6-the-series"),
        ("login", r"/login"),
        ("favorites", r"/favorites"),
    ),
    ans=[
        num("animation_count", 25),
        num("scifi_count", 10),
        num("star_count", 2),
        phrase("first_star_title", "LEGO Star Wars: Droid Tales"),
        phrase("first_star_year", "2015"),
        phrase("duck_rating", "TV-Y7"),
        phrase("duck_year", "2017"),
        phrase("bh6_title", "Big Hero 6: The Series"),
        phrase("bh6_rating", "TV-Y7"),
        num("bob_favorites_total", 4),
        num("bob_shows_saved", 3),
    ],
    db="""    check_only_tables_changed(judge, initial, after, {"favorites"})
    check_rows_added(judge, initial, after, "favorites", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites WHERE user_id=2 AND item_type='show' AND item_key='big-hero-6-the-series'",
        (), "bob_faved_bh6")
""",
)

# ---------------------------------------------------------------- T4
SPEC[4] = dict(
    note="""    r2 note: the site-wide search now lists full result sets, so the
    printed Parks & Entertainment count is the true match count (13;
    was capped at 12 with the r1 mirror).
""",
    nav=nav(
        ("mickey_search", r"/search\?[^\" ]*q=mickey"),
        ("mm_detail", r"/shows/disney-mickey-mouse"),
        ("shows_variety", r"/shows\?[^\" ]*genre=Variety"),
        ("variety_first_detail", r"/shows/disney-mickey-mouse"),
        ("shows_all", r"/shows\?[^\" ]*genre=&|/shows$|/shows\?"),
        ("login", r"/login"),
        ("favorites", r"/favorites"),
        ("duck_search", r"/shows\?[^\" ]*q=duck"),
    ),
    ans=[
        num("mickey_shows", 2),
        num("mickey_parks_entertainment", 13),
        phrase("mm_rating", "TV-G"),
        num("variety_count", 3),
        num("shows_total", 54),
        num("carol_favorites_total", 3),
        num("duck_count", 3),
    ],
    db="""    check_only_tables_changed(judge, initial, after, {"favorites"})
    check_rows_added(judge, initial, after, "favorites", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites WHERE user_id=3 AND item_type='show' AND item_key='disney-mickey-mouse'",
        (), "carol_faved_mickey_mouse")
""",
)

# ---------------------------------------------------------------- T5
SPEC[5] = dict(
    note="""    Known defect (pinned): the DuckTales rating answer is stable (both
    same-titled shows are TV-Y7) but the release year is not (1987/2017);
    this task only asks for the rating, which stays deterministic.
""",
    nav=nav(
        ("shows_all", r"/shows"),
        ("shows_comedy", r"/shows\?[^\" ]*genre=Comedy"),
        ("shows_fantasy", r"/shows\?[^\" ]*genre=Fantasy"),
        ("fantasy_first_detail", r"/shows/adventures-of-the-gummi-bears"),
        ("login", r"/login"),
        ("duck_search", r"/shows\?[^\" ]*q=duck"),
    ) + navany("ducktales_detail", [r"/shows/ducktales-products", r"/shows/ducktales$|/shows/ducktales\?"]) + nav(
        ("comedy_title_sort", r"/shows\?[^\" ]*genre=Comedy[^\" ]*sort=title|/shows\?[^\" ]*sort=title[^\" ]*genre=Comedy"),
    ),
    ans=[
        num("shows_total", 54),
        num("comedy_count", 25),
        num("fantasy_count", 9),
        phrase("first_fantasy", "Adventures of the Gummi Bears"),
        phrase("fantasy_year", "1985"),
        num("duck_count", 3),
        phrase("duck_rating", "TV-Y7"),
        phrase("first_comedy", "Austin & Ally"),
        phrase("comedy_rating", "TV-G"),
    ],
    db="""    check_only_tables_changed(judge, initial, after, {"favorites"})
    check_rows_added(judge, initial, after, "favorites", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites WHERE user_id=2 AND item_type='show' AND item_key='adventures-of-the-gummi-bears'",
        (), "bob_faved_gummi_bears")
""",
)

# ---------------------------------------------------------------- T6
SPEC[6] = dict(
    note="",
    nav=nav(
        ("mk_thrill", r"/parks/attractions\?[^\" ]*park=magic-kingdom[^\" ]*interest=Thrill\+Rides|/parks/attractions\?[^\" ]*interest=Thrill\+Rides[^\" ]*park=magic-kingdom"),
        ("mk_thrill_40", r"/parks/attractions\?[^\" ]*height=40"),
        ("first_detail", r"/parks/attractions/magic-kingdom/space-mountain"),
        ("mk_thrill_48", r"/parks/attractions\?[^\" ]*height=48"),
        ("tron_detail", r"/parks/attractions/magic-kingdom/tron-lightcycle-run"),
        ("mk_entertainment", r"/parks/attractions\?[^\" ]*type=Entertainment"),
    ),
    ans=[
        num("mk_thrill_count", 5),
        num("mk_thrill_40_count", 3),
        phrase("first_name", "Space Mountain"),
        phrase("first_height", '44" or taller'),
        anyph("first_interest", ["Big Drops", "Dark", "Thrill Rides", "Adults"]),
        num("mk_thrill_again", 5),
        num("h48_count", 1),
        phrase("h48_name", "TRON Lightcycle / Run"),
        num("mk_entertainment_count", 26),
    ],
    db=READ_ONLY_DB,
)

# ---------------------------------------------------------------- T7
SPEC[7] = dict(
    note="""    r2 note: the task now names "the Heartbeat of Freedom fireworks
    show at EPCOT" (two EPCOT fireworks exist; the name is
    deterministic), and the favorites toggle now stores the full
    park/slug key with the card rendering on /favorites (count ==
    rendered cards == 4).
""",
    nav=nav(
        ("char_exp_all", r"/parks/attractions\?[^\" ]*type=Entertainment[^\" ]*interest=Character\+Experiences|/parks/attractions\?[^\" ]*interest=Character\+Experiences[^\" ]*type=Entertainment"),
        ("char_exp_mk", r"/parks/attractions\?[^\" ]*park=magic-kingdom"),
        ("mk_first_detail", r"/parks/attractions/magic-kingdom/starlight-dream-night-away-parade"),
        ("fireworks", r"/parks/attractions\?[^\" ]*interest=Fireworks"),
        ("login", r"/login"),
        ("favorites", r"/favorites"),
        ("epcot_fireworks_detail", r"/parks/attractions/epcot/heartbeat-of-freedom"),
    ),
    ans=[
        num("char_exp_all_count", 44),
        num("char_exp_mk_count", 12),
        phrase("mk_first_name", "Disney Starlight: Dream the Night Away"),
        num("fireworks_count", 6),
        num("alice_favorites_total", 4),
    ],
    db="""    check_only_tables_changed(judge, initial, after, {"favorites"})
    check_rows_added(judge, initial, after, "favorites", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites WHERE user_id=1 AND item_type='attraction' "
        "AND item_key='epcot/heartbeat-of-freedom'",
        (), "alice_faved_heartbeat_of_freedom")
""",
)

# ---------------------------------------------------------------- T8
SPEC[8] = dict(
    note="",
    nav=nav(
        ("attractions_all", r"/parks/attractions\?[^\" ]*type=Attraction"),
        ("h38", r"/parks/attractions\?[^\" ]*height=38"),
        ("h44", r"/parks/attractions\?[^\" ]*height=44"),
        ("h48", r"/parks/attractions\?[^\" ]*height=48"),
        ("height_sort", r"/parks/attractions\?[^\" ]*sort=height"),
        ("first_detail", r"/parks/attractions/blizzard-beach/downhill-double-dipper"),
        ("last_detail", r"/parks/attractions/magic-kingdom/tron-lightcycle-run"),
        ("big_drops", r"/parks/attractions\?[^\" ]*interest=Big\+Drops"),
    ),
    ans=[
        num("attractions_total", 160),
        num("h38_count", 22),
        num("h44_count", 8),
        num("h48_count", 5),
        phrase("first_name", "Downhill Double Dipper"),
        phrase("first_park", "Disney's Blizzard Beach Water Park"),
        phrase("last_name", "TRON Lightcycle / Run"),
        phrase("last_park", "Magic Kingdom Park"),
        num("attractions_total_again", 160),
        num("big_drops_count", 8),
    ],
    db=READ_ONLY_DB,
)

# ---------------------------------------------------------------- T9
SPEC[9] = dict(
    note="""    r2 note: the favorites toggle now stores the full park/slug key,
    so Dana's favorited Soarin' card renders on /favorites (count ==
    rendered cards == 4).
""",
    nav=nav(
        ("mk_thrill", r"/parks/attractions\?[^\" ]*park=magic-kingdom[^\" ]*interest=Thrill\+Rides|/parks/attractions\?[^\" ]*interest=Thrill\+Rides[^\" ]*park=magic-kingdom"),
        ("dwarfs_detail", r"/parks/attractions/magic-kingdom/seven-dwarfs-mine-train"),
        ("mk_dark", r"/parks/attractions\?[^\" ]*interest=Dark"),
        ("pirates_detail", r"/parks/attractions/magic-kingdom/pirates-of-the-caribbean"),
        ("related_detail", r"/parks/attractions/magic-kingdom/pirates-adventures"),
        ("epcot_slow", r"/parks/attractions\?[^\" ]*park=epcot[^\" ]*interest=Slow\+Rides|/parks/attractions\?[^\" ]*interest=Slow\+Rides[^\" ]*park=epcot"),
        ("soarin_detail", r"/parks/attractions/epcot/soarin-around-world"),
        ("login", r"/login"),
        ("favorites", r"/favorites"),
    ),
    ans=[
        num("mk_thrill_count", 5),
        phrase("dwarfs_height", '38" or taller'),
        phrase("dwarfs_heading", "Heigh-Ho, It's Off You Go!"),
        num("mk_dark_count", 4),
        phrase("pirates_park", "Magic Kingdom Park"),
        phrase("related_name", "A Pirate's Adventure ~ Treasures of the Seven Seas"),
        phrase("related_park", "Magic Kingdom Park"),
        num("epcot_slow_count", 9),
        phrase("soarin_park", "EPCOT"),
        num("dana_favorites_total", 4),
    ],
    db="""    check_only_tables_changed(judge, initial, after, {"favorites"})
    check_rows_added(judge, initial, after, "favorites", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites WHERE user_id=4 AND item_type='attraction' AND item_key='epcot/soarin-around-world'",
        (), "dana_faved_soarin")
""",
)

# ---------------------------------------------------------------- T10
SPEC[10] = dict(
    note="",
    nav=nav(
        ("toys_sorted", r"/shop/toys\?[^\" ]*sort=price_high"),
        ("top_detail", r"/shop/products/416120689757"),
        ("bag", r"/bag"),
        ("checkout", r"/checkout"),
        ("order_confirmed", r"/order/DS"),
        ("action_figures", r"/shop/toys\?[^\" ]*category=Action\+Figures"),
    ),
    ans=[
        num("toys_count", 48),
        phrase("most_expensive", "Disney Princess Classic Doll Collection Gift Set"),
        phrase("price", "149.99"),
        phrase("rating", "1.0"),
        phrase("bag_line_2x", "299.98"),
        phrase("bag_line_1x", "149.99"),
        phrase("order_total", "149.99"),
        regex("confirmation", r"DS[0-9A-F]{7}"),
        num("action_figures_count", 15),
    ],
    db="""    check_only_tables_changed(judge, initial, after, {"cart_items", "shop_orders"})
    check_rows_added(judge, initial, after, "shop_orders", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM shop_orders WHERE email='toy.buyer@example.com' AND total=149.99",
        (), "order_row")
    check_rows_added(judge, initial, after, "cart_items", 0)
""",
)

# ---------------------------------------------------------------- T11
SPEC[11] = dict(
    note="""    r2 note: the task no longer asks for an original price (upstream sale
    items carry none; the page renders no strike-through), so that
    sub-answer is gone from the contract.
""",
    nav=nav(
        ("sale", r"/shop/sale"),
        ("sale_mickey_sorted", r"/shop/sale\?[^\" ]*character=Mickey\+Mouse[^\" ]*sort=rating|/shop/sale\?[^\" ]*sort=rating[^\" ]*character=Mickey\+Mouse"),
        ("top_detail", r"/shop/products/415130694607"),
        ("bag", r"/bag"),
        ("accessories_bags", r"/shop/accessories\?[^\" ]*category=Bags"),
        ("first_bag_detail", r"/shop/products/442111075919"),
    ),
    ans=[
        num("sale_count", 6),
        num("sale_mickey_count", 3),
        phrase("top_rated", "Mickey Mouse Halloween 2026 Plush"),
        phrase("price", "29.99"),
        phrase("rating", "5.0"),
        phrase("bag_total", "29.99"),
        num("bags_wallets_count", 17),
        phrase("first_bag", "Mickey Mouse Tote by Harveys"),
        phrase("first_bag_price", "198.00"),
        num("first_bag_reviews", 7),
        phrase("new_bag_total", "227.99"),
    ],
    db="""    check_only_tables_changed(judge, initial, after, {"cart_items"})
    check_rows_added(judge, initial, after, "cart_items", 2)
    check_row_matches(judge, after,
        "SELECT 1 FROM cart_items WHERE product_pid='415130694607' AND qty=1",
        (), "bag_row_plush")
    check_row_matches(judge, after,
        "SELECT 1 FROM cart_items WHERE product_pid='442111075919' AND qty=1",
        (), "bag_row_tote")
""",
)

# ---------------------------------------------------------------- T12
SPEC[12] = dict(
    note="",
    nav=nav(
        ("clothes_adults_sorted", r"/shop/clothing\?[^\" ]*target_age=Adults"),
        ("cheapest_detail", r"/shop/products/5106057431232m"),
        ("toys_plush_sorted", r"/shop/toys\?[^\" ]*category=Plush[^\" ]*sort=price_low|/shop/toys\?[^\" ]*sort=price_low[^\" ]*category=Plush"),
        ("plush_detail", r"/shop/products/463521109001"),
        ("bag", r"/bag"),
    ),
    ans=[
        num("adults_count", 25),
        phrase("cheapest_adult", "Mickey and Minnie Mouse Cutie Ghost T-Shirt for Women"),
        phrase("price", "36.99"),
        phrase("rating", "3.5"),
        anyph("bare_necessity", ["60% cotton / 40% polyester", "Imported"]),
        phrase("cheapest_plush", "Mickey Mouse Mini Plush Magnet"),
        num("combined_total", 127.96),
    ],
    db="""    check_only_tables_changed(judge, initial, after, {"cart_items"})
    check_rows_added(judge, initial, after, "cart_items", 2)
    check_row_matches(judge, after,
        "SELECT 1 FROM cart_items WHERE product_pid='5106057431232m' AND qty=3",
        (), "bag_row_tshirt")
    check_row_matches(judge, after,
        "SELECT 1 FROM cart_items WHERE product_pid='463521109001' AND qty=1",
        (), "bag_row_plush")
""",
)

# ---------------------------------------------------------------- T13
SPEC[13] = dict(
    note="""    r2 note: the search now lists the full Shop result set (25 plush
    products, count == listed rows), and the task no longer asks for the
    first plush's review count (upstream has none for it).
""",
    nav=nav(
        ("plush_search", r"/search\?[^\" ]*q=plush"),
        ("first_plush_detail", r"/shop/products/194735352982"),
        ("tote_search", r"/search\?[^\" ]*q=tote"),
        ("first_tote_detail", r"/shop/products/442030853759"),
        ("bag", r"/bag"),
        ("checkout", r"/checkout"),
        ("order_confirmed", r"/order/DS"),
    ),
    ans=[
        num("plush_count", 25),
        phrase("first_plush", "Blaze Manoukian's Pet Pig Plush with Sound by Mattel"),
        phrase("first_plush_price", "32.99"),
        phrase("first_tote", "Disneyland Canvas Tote"),
        phrase("bag_total_before", "122.97"),
        phrase("bag_total_after", "89.98"),
        num("bag_items_after", 1),
        phrase("order_total", "89.98"),
        regex("confirmation", r"DS[0-9A-F]{7}"),
    ],
    db="""    check_only_tables_changed(judge, initial, after, {"cart_items", "shop_orders"})
    check_rows_added(judge, initial, after, "shop_orders", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM shop_orders WHERE email='shop.compare@example.com' AND total=89.98",
        (), "order_row")
    check_rows_added(judge, initial, after, "cart_items", 0)
""",
)

# ---------------------------------------------------------------- T14
SPEC[14] = dict(
    note="""    r2 note: the task now uses the upstream official casing "Magic in the
    Stars" exactly as the schedule filter lists it.
""",
    nav=nav(
        ("doi_schedule", r"/live-shows/disney-on-ice"),
        ("mits_filter", r"/live-shows/disney-on-ice\?[^\" ]*show=Magic\+in\+the\+Stars"),
        ("ca_search", r"/live-shows/disney-on-ice\?[^\" ]*q=CA"),
        ("city_sort", r"/live-shows/disney-on-ice\?[^\" ]*sort=city"),
        ("albany_detail", r"/live-shows/disney-on-ice/121030"),
        ("booking", r"/live-shows/disney-on-ice/121030/book"),
        ("ticket_confirmed", r"/tickets/TK"),
    ),
    ans=[
        num("mits_count", 15),
        num("ca_count", 8),
        phrase("first_city", "Albany, NY"),
        phrase("venue", "MVP Arena"),
        num("performances", 4),
        phrase("booked_day", "Jan 21, 2027"),
        phrase("booked_time", "7:00 pm"),
        phrase("ticket_total", "70.00"),
        regex("confirmation", r"TK[0-9A-F]{7}"),
    ],
    db="""    check_only_tables_changed(judge, initial, after, {"ticket_orders"})
    check_rows_added(judge, initial, after, "ticket_orders", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM ticket_orders WHERE email='ice.first@example.com' "
        "AND event_id='121030' AND qty=2 AND total=70.0 AND day='Jan 21, 2027' AND time='7:00 pm'",
        (), "ticket_row")
""",
)

# ---------------------------------------------------------------- T15
SPEC[15] = dict(
    note="",
    nav=nav(
        ("kent_search", r"/live-shows/disney-on-ice\?[^\" ]*q=Kent"),
        ("kent_detail", r"/live-shows/disney-on-ice/120960"),
        ("booking", r"/live-shows/disney-on-ice/120960/book[^\" ]*day=Oct\+24|/live-shows/disney-on-ice/120960/book"),
        ("ticket_confirmed", r"/tickets/TK"),
        ("jii_filter", r"/live-shows/disney-on-ice\?[^\" ]*show=Jump\+In!"),
        ("jii_city_sort", r"/live-shows/disney-on-ice\?[^\" ]*sort=city[^\" ]*show=Jump\+In!|/live-shows/disney-on-ice\?[^\" ]*show=Jump\+In![^\" ]*sort=city"),
    ),
    ans=[
        phrase("venue", "accesso ShoWare Center"),
        phrase("date_range", "Oct 22-25, 2026"),
        phrase("booked_day", "Oct 24, 2026"),
        phrase("booked_time", "11:00 am"),
        phrase("ticket_total", "105.00"),
        regex("confirmation", r"TK[0-9A-F]{7}"),
        num("jii_count", 16),
        phrase("jii_first_city", "Anaheim, CA"),
        phrase("jii_first_venue", "Honda Center"),
    ],
    db="""    check_only_tables_changed(judge, initial, after, {"ticket_orders"})
    check_rows_added(judge, initial, after, "ticket_orders", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM ticket_orders WHERE email='skate.fan@example.com' "
        "AND event_id='120960' AND qty=3 AND total=105.0 AND day='Oct 24, 2026' AND time='11:00 am'",
        (), "ticket_row")
""",
)

# ---------------------------------------------------------------- T16
SPEC[16] = dict(
    note="""    r2 redesign: the task is one real multi-city planning chain measured
    at 18 honest atomic steps by the r2 reviewer's own two-round
    Chromium walks (the per-performance Buy Tickets link prefills
    day+time; changing the prefilled 1:00 pm to the task-required
    5:00 pm performance is a genuinely required step).
""",
    nav=nav(
        ("live_shows", r"/live-shows($|\?)"),
        ("doi_schedule", r"/live-shows/disney-on-ice"),
        ("fyh_filter", r"/live-shows/disney-on-ice\?[^\" ]*show=Find\+Your\+Hero"),
        ("tx_search", r"/live-shows/disney-on-ice\?[^\" ]*q=TX"),
        ("city_sort", r"/live-shows/disney-on-ice\?[^\" ]*sort=city"),
        ("laredo_detail", r"/live-shows/disney-on-ice/120991"),
        ("booking", r"/live-shows/disney-on-ice/120991/book"),
        ("ticket_confirmed", r"/tickets/TK"),
        ("mof_filter", r"/live-shows/disney-on-ice\?[^\" ]*show=Magic\+of\+Family"),
    ),
    ans=[
        num("broadway_musicals", 3),
        num("events_total", 89),
        num("fyh_count", 18),
        num("tx_count", 5),
        phrase("laredo_venue", "Sames Auto Arena"),
        phrase("laredo_dates", "Nov 20-22, 2026"),
        phrase("booked_day", "Nov 22, 2026"),
        phrase("booked_time", "5:00 pm"),
        phrase("ticket_total", "70.00"),
        regex("confirmation", r"TK[0-9A-F]{7}"),
        num("mof_count", 19),
    ],
    db="""    check_only_tables_changed(judge, initial, after, {"ticket_orders"})
    check_rows_added(judge, initial, after, "ticket_orders", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM ticket_orders WHERE email='laredo.ice@example.com' "
        "AND event_id='120991' AND qty=2 AND total=70.0 AND day='Nov 22, 2026' AND time='5:00 pm'",
        (), "ticket_row")
""",
)

# ---------------------------------------------------------------- T17
SPEC[17] = dict(
    note="""    r2 note: game titles are the clean hub names (no CMS artifacts), the
    availability line renders as a badge, and the description is real
    upstream rich text under a Description heading — the games search for
    'disney' now matches 3 of the 4 games (Gargoyles Remastered is clean).
""",
    nav=nav(
        ("signup", r"/signup"),
        ("games", r"/games"),
        ("games_search", r"/games\?[^\" ]*q=disney"),
        ("illusion_detail", r"/games/disney-illusion-island"),
        ("cafe_detail", r"/games/disney-villains-cursed-cafe"),
        ("login", r"/login"),
        ("favorites", r"/favorites"),
    ),
    ans=[
        num("games_total", 4),
        num("disney_games_count", 3),
        phrase("illusion_title", "Disney Illusion Island"),
        phrase("illusion_first_sentence", "Join Mickey & Friends on a quest to explore the mysterious island of Monoth and recover three mystical books to save the world from disaster!"),
        phrase("cafe_title", "Disney Villains Cursed Café"),
        num("favorites_total", 2),
        phrase("fav_one", "Disney Illusion Island"),
        phrase("fav_two", "Disney Villains Cursed Café"),
    ],
    db="""    check_only_tables_changed(judge, initial, after, {"users", "favorites"})
    check_rows_added(judge, initial, after, "users", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM users WHERE email='game.player@test.com' AND name='Game Player'",
        (), "game_account")
    check_rows_added(judge, initial, after, "favorites", 2)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites f JOIN users u ON f.user_id=u.id "
        "WHERE u.email='game.player@test.com' AND f.item_type='game' "
        "AND f.item_key IN ('disney-illusion-island', 'disney-villains-cursed-cafe')",
        (), "game_fav_1")
""",
)

# ---------------------------------------------------------------- T18
SPEC[18] = dict(
    note="",
    nav=nav(
        ("frozen_search", r"/search\?[^\" ]*q=frozen"),
        ("fea_detail", r"/parks/attractions/epcot/frozen-ever-after"),
        ("frozen3_detail", r"/movies/frozen-3"),
        ("login", r"/login"),
        ("favorites", r"/favorites"),
        ("stitch_search", r"/search\?[^\" ]*q=stitch"),
        ("stitch_detail", r"/shop/products/415161238870"),
        ("bag", r"/bag"),
    ),
    ans=[
        num("frozen_movies", 1),
        num("frozen_parks_entertainment", 3),
        phrase("fea_park", "EPCOT"),
        phrase("fea_height", "Any height"),
        phrase("movie_title", "Frozen 3"),
        phrase("movie_rating", "Not Yet Rated"),
        phrase("movie_date", "November 24, 2027"),
        num("dana_favorites_total", 4),
        num("stitch_products", 5),
        phrase("first_stitch", "Stitch Knit Plush"),
        phrase("stitch_price", "24.99"),
        phrase("bag_total", "24.99"),
    ],
    db="""    check_only_tables_changed(judge, initial, after, {"favorites", "cart_items"})
    check_rows_added(judge, initial, after, "favorites", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites WHERE user_id=4 AND item_type='movie' AND item_key='frozen-3'",
        (), "dana_faved_frozen3")
    check_rows_added(judge, initial, after, "cart_items", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM cart_items WHERE product_pid='415161238870' AND qty=1",
        (), "bag_row_stitch")
""",
)

# ---------------------------------------------------------------- T19
SPEC[19] = dict(
    note="""    r2 note: the parks hub now shows real display names for all locations
    (no bare slugs; listed count 10 and EPCOT's 72 unaffected), and the
    favorites toggle stores the full park/slug key so Carol's favorited
    card renders on /favorites (count == rendered cards == 3).
""",
    nav=nav(
        ("parks_hub", r"/parks($|\?)"),
        ("epcot_attractions", r"/parks/attractions\?[^\" ]*park=epcot[^\" ]*type=Attraction|/parks/attractions\?[^\" ]*type=Attraction[^\" ]*park=epcot"),
        ("first_detail", r"/parks/attractions/epcot/mission-space-advanced-training-lab"),
        ("epcot_charexp", r"/parks/attractions\?[^\" ]*park=epcot[^\" ]*type=Entertainment[^\" ]*interest=Character\+Experiences"),
        ("charexp_detail", r"/parks/attractions/epcot/visa-card-character-experience"),
        ("login", r"/login"),
        ("favorites", r"/favorites"),
    ),
    ans=[
        num("parks_listed", 10),
        phrase("most_park", "EPCOT"),
        num("most_park_count", 72),
        num("epcot_attractions_count", 41),
        phrase("first_attraction", "Advanced Training Lab"),
        phrase("first_height", "Any height"),
        num("epcot_charexp_count", 15),
        phrase("first_charexp", "Disney® Visa® Cardmember Photo Opportunity at EPCOT"),
        num("carol_favorites_total", 3),
    ],
    db="""    check_only_tables_changed(judge, initial, after, {"favorites"})
    check_rows_added(judge, initial, after, "favorites", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites WHERE user_id=3 AND item_type='attraction' AND item_key='epcot/visa-card-character-experience'",
        (), "carol_faved_visa_charexp")
""",
)


def main():
    for n in sorted(SPEC):
        spec = SPEC[n]
        emit(n, spec["note"], spec["nav"], spec["ans"], spec["db"])


if __name__ == "__main__":
    main()
