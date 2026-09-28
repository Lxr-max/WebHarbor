#!/usr/bin/env python3
"""Generate the 21 per-task verifier modules (verify_0.py .. verify_20.py).

Ground truth is frozen from the seed database + live re-review walks and is
HARDCODED here (never in tasks.jsonl). Run from sites/sourceforge/verify/:
    python3 make_verifiers.py

r3 sync (fb4ff5bf): TASKS check specs updated for the 5 deepened tasks
(T3/T4/T5/T12/T19); the other 16 specs unchanged. Expected values re-frozen
from the r3 review container (wh-sf-r3) honest walks + seed DB.
"""
import re
from pathlib import Path

HEADER = '''#!/usr/bin/env python3
"""Verify SourceForge--{n}.

{question}
"""
from verify_lib import (check_answer_number, check_answer_phrase, check_read_only,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff, check_answer_any, check_answer_phrase_near)

TASK_ID = "SourceForge--{n}"

'''

FOOTER = '''

def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
{checks}
{state}

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
'''

RO = '''    check_read_only(judge, initial_db, after_db)
'''

# The 21 task texts, byte-identical to sites/sourceforge/tasks.jsonl (r2).
import json
Q = {}
for _line in (Path(__file__).resolve().parent.parent / "tasks.jsonl").read_text(encoding="utf-8").splitlines():
    _row = json.loads(_line)
    Q[int(_row["id"].split("--")[1])] = _row["ques"]

# per-task: list of (kind, args) emitted as checks
def B(subject, *competitors, near=None, window=420, near_window=80,
      context=None, context_window=80):
    """Binding spec: (subject, competitors, near, window, near_window, context, context_window)."""
    return (subject, competitors, near, window, near_window, context, context_window)


def _kw(subject, competitors, near, window, near_window, context=None, context_window=80):
    parts = [f"subject={subject!r}"]
    if competitors:
        parts.append(f"competitors={list(competitors)!r}")
    if window != 420:
        parts.append(f"window={window}")
    if near:
        parts.append(f"near={near!r}")
    if near_window != 80:
        parts.append(f"near_window={near_window}")
    if context:
        parts.append(f"context={list(context)!r}")
    if context and context_window != 80:
        parts.append(f"context_window={context_window}")
    return ", ".join(parts)


def num(name, value, label, spec):
    return (f'    check_answer_number(judge, answer, "{name}", {value!r}, {label!r}, '
            f'{_kw(*spec)})')


def phrase(name, text):
    return f'    check_answer_phrase(judge, answer, "{name}", {text!r})'


def phrase_near(name, text, spec):
    return (f'    check_answer_phrase_near(judge, answer, "{name}", {text!r}, '
            f'{_kw(*spec)})')


def path(name, pattern):
    return f'    check_visited_path(judge, traj, "{name}", r"{pattern}")'


def anyof(name, variants, label, spec):
    return (f'    check_answer_any(judge, answer, "{name}", {variants!r}, {label!r}, '
            f'{_kw(*spec)})')

TASKS = {}

TASKS[0] = [
    ("path", "sorted_search", r"/directory/\?q=file(\+|%20)compression.*sort=popular"),
    ("path", "visited_mingw", r"/projects/mingw/"),
    ("path", "visited_autoclicker", r"/projects/orphamielautoclicker/"),
    ("path", "visited_7zip", r"/projects/sevenzip/"),
    ("path", "visited_reviews_for_ratings", r"/projects/(mingw|orphamielautoclicker|sevenzip)/reviews/"),
    ("p", "mingw_name", "MinGW"),
    ("n", "mingw_week", "3,600,000", "MinGW weekly downloads"),
    ("p", "mingw_reg", "2000-02-09"),
    ("p", "mingw_license", "GPLv3"),
    ("n", "mingw_rating", "4.6", "MinGW rating"),
    ("n", "mingw_reviews", 171, "MinGW review count"),
    ("p", "auto_name", "AutoClicker"),
    ("n", "auto_week", "768,800", "AutoClicker weekly downloads"),
    ("p", "auto_reg", "2014-06-19"),
    ("p", "auto_license", "Creative Commons Attribution Non-Commercial"),
    ("n", "auto_rating", "4.9", "AutoClicker rating"),
    ("n", "auto_reviews", 221, "AutoClicker review count"),
    ("n", "sz_week", 23587, "7-Zip weekly downloads"),
    ("p", "sz_reg", "2000-11-10"),
    ("p", "sz_license", "GNU Library or Lesser General Public License version 2.0"),
    ("n", "sz_rating", "4.8", "7-Zip rating"),
    ("n", "sz_reviews", 831, "7-Zip review count"),
    ("p", "sz_updated_more_recent", "2026-09-04"),
]

TASKS[1] = [
    ("path", "visited_files", r"/projects/sevenzip/files/"),
    ("path", "visited_2603_folder", r"/projects/sevenzip/files/7-Zip/26\.03/"),
    ("path", "visited_2602_folder", r"/projects/sevenzip/files/7-Zip/26\.02/"),
    ("path", "visited_project_page", r"/projects/sevenzip/$"),
    ("path", "visited_download_page", r"7z2603-x64\.exe/download"),
    ("path", "visited_stats_timeline", r"/stats/timeline"),
    ("path", "visited_stats_os", r"/stats/os"),
    ("p", "build_arm64", "7z2603-arm64.exe"),
    ("p", "build_extra", "7z2603-extra.7z"),
    ("p", "build_linux", "7z2603-linux-x64.tar.xz"),
    ("p", "build_src", "7z2603-src.7z"),
    ("p", "build_x64_exe", "7z2603-x64.exe"),
    ("p", "build_x64_msi", "7z2603-x64.msi"),
    ("p", "build_x86", "7z2603.exe"),
    ("p", "build_2602_x64", "7z2602-x64.exe"),
    ("p", "build_2602_msi", "7z2602-x64.msi"),
    ("p", "build_2602_x86", "7z2602.exe"),
    ("n", "folder_week_2603", 29589, "26.03 folder weekly count"),
    ("n", "folder_week_2602", 21750, "26.02 folder weekly count"),
    ("p", "download_button_target", "7z2603-x64.exe"),
    ("p", "peak_day", "2026-09-19"),
    ("n", "peak_day_count", "6,001", "peak day downloads"),
    ("p", "top_os", "Windows"),
    ("n", "top_os_count", "90,456", "Windows downloads"),
]

TASKS[2] = [
    ("path", "visited_sz_reviews", r"/projects/sevenzip/reviews/"),
    ("path", "visited_sz_4star_filter", r"/projects/sevenzip/reviews/\?filter-stars=4"),
    ("path", "visited_kp_reviews", r"/projects/keepass/reviews/"),
    ("path", "visited_kp_5star_filter", r"/projects/keepass/reviews/\?filter-stars=5"),
    ("path", "visited_kp_4star_filter", r"/projects/keepass/reviews/\?filter-stars=4"),
    ("n", "sz_avg", "4.8", "7-Zip overall rating"),
    ("n", "sz_five_star", 765, "7-Zip 5-star count"),
    ("n", "sz_one_star", 27, "7-Zip 1-star count"),
    ("p", "featured_author", "itreet-raking5"),
    ("p", "featured_text", "This is my tribute to your great 7-zip"),
    ("n", "sz_four_star_view", 6, "7-Zip 4-star filter view count"),
    ("n", "kp_avg", "4.9", "KeePass overall rating"),
    ("n", "kp_five_star", 567, "KeePass 5-star count"),
    ("n", "kp_one_star", 11, "KeePass 1-star count"),
    ("n", "kp_five_star_view", 22, "KeePass 5-star filter view count"),
    ("n", "kp_four_star_view", 3, "KeePass 4-star filter view count"),
    ("n", "sz_total_reviews", 831, "7-Zip total reviews"),
    ("n", "kp_total_reviews", 606, "KeePass total reviews"),
]

TASKS[3] = [
    ("path", "visited_bugs", r"/p/sevenzip/bugs/"),
    ("path", "visited_progress_search", r"/p/sevenzip/bugs/search/.*progress"),
    ("path", "visited_ticket_2701", r"/p/sevenzip/bugs/2701/"),
    ("path", "visited_cve_search", r"/p/sevenzip/bugs/search/.*CVE"),
    ("path", "visited_ticket_2681", r"/p/sevenzip/bugs/2681/"),
    ("path", "visited_ticket_2670", r"/p/sevenzip/bugs/2670/"),
    ("path", "visited_ticket_2669", r"/p/sevenzip/bugs/2669/"),
    ("p", "ticket_summary", "user interface misleading"),
    ("p", "ticket_status_open", "open"),
    ("p", "ticket_creator", "Harry Stein"),
    ("n", "ticket_priority", 5, "ticket 2701 priority"),
    ("p", "owner_reply", "Maybe your usb was slow"),
    ("n", "cve_ticket_count", 3, "CVE search results"),
    ("p", "cve_newest_1", "2681"),
    ("p", "cve_newest_1_summary", "CVE-2026-58052"),
    ("n", "cve_newest_1_priority", 7, "ticket 2681 priority"),
    ("p", "cve_newest_2", "2670"),
    ("p", "cve_newest_2_summary", "CVE-2026-48102"),
    ("n", "cve_newest_2_priority", 7, "ticket 2670 priority"),
    ("p", "cve_lowest", "2669"),
    ("p", "cve_lowest_owner", "Igor Pavlov"),
    ("p", "cve_lowest_created", "2026-06-10"),
    ("n", "open_tickets", 31, "open ticket count"),
]

TASKS[4] = [
    ("path", "visited_forum", r"/p/sevenzip/discussion/45797/"),
    ("path", "visited_darkmode_thread", r"/thread/0f17be73d3/"),
    ("path", "visited_darktheme_thread", r"/thread/768a550c16/"),
    ("path", "visited_highview_thread", r"/thread/b8d64839d0/"),
    ("path", "visited_help_forum", r"/p/sevenzip/discussion/45798/"),
    ("path", "visited_help_hv_thread", r"/thread/be65c1f094/"),
    ("p", "thread_subject", "Dark Mode"),
    ("p", "thread_creator", "Carlos Nunes"),
    ("p", "thread_created", "Tue Jul 08, 2025"),
    ("n", "thread_posts", 4, "Dark Mode posts"),
    ("n", "thread_views", "3,206", "Dark Mode views"),
    ("p", "darkmode_health_reason", "greatly facilitates eye comfort"),
    ("p", "darktheme_creator", "kb0000001"),
    ("n", "darktheme_posts", 18, "Dark Theme posts"),
    ("n", "darktheme_views", "9,620", "Dark Theme views"),
    ("p", "darktheme_opening_post", "Dark Theme"),
    ("p", "max_views_thread", "7-Zip 26.02"),
    ("p", "max_views_creator", "Igor Pavlov"),
    ("n", "max_views", "297,148", "highest-view thread view count"),
    ("p", "help_forum_name", "Help"),
    ("any", "help_topic_count", ["25", "8,276", "8276"], "topics the Help forum lists"),
    ("p", "help_hv_subject", "Compress multiple files to individual ZIP archives with fixed size"),
    ("p", "help_hv_creator", "rtm"),
    ("n", "help_hv_views", "3,161", "Help forum highest-viewed thread views"),
]

TASKS[5] = [
    ("path", "visited_top", r"/top"),
    ("path", "visited_corefonts", r"/projects/corefonts/"),
    ("path", "visited_mingw", r"/projects/mingw/"),
    ("path", "visited_npp", r"/projects/npppluginmgr/"),
    ("path", "visited_corefonts_reviews", r"/projects/corefonts/reviews/"),
    ("path", "visited_mingw_reviews", r"/projects/mingw/reviews/"),
    ("path", "visited_npp_reviews", r"/projects/npppluginmgr/reviews/"),
    ("path", "visited_7zip", r"/projects/sevenzip/"),
    ("path", "visited_7zip_reviews", r"/projects/sevenzip/reviews/"),
    ("p", "alltime_no1", "TrueType core fonts"),
    ("p", "alltime_no1_downloads", "3.3B"),
    ("p", "weekly_no1", "MinGW"),
    ("p", "weekly_no1_downloads", "3.6M"),
    ("p", "sz_alltime_rank", "10"),
    ("any", "sz_alltime_total", ["430M", "430.1M", "430,100,000"], "7-Zip all-time total as displayed"),
    ("p", "corefonts_reg", "2001-08-22"),
    ("p", "mingw_reg", "2000-02-09"),
    ("p", "npp_reg", "2011-11-29"),
    ("n", "corefonts_week", "3,000,000", "corefonts weekly downloads"),
    ("n", "mingw_week", "3,600,000", "MinGW weekly downloads"),
    ("n", "npp_week", "109,095", "Notepad++ Plugin Manager weekly downloads"),
    ("p", "corefonts_license", "GPLv2"),
    ("p", "mingw_license", "GPLv3"),
    ("n", "corefonts_rating", "4.1", "corefonts rating"),
    ("n", "corefonts_reviews", 46, "corefonts review count"),
    ("n", "mingw_rating", "4.6", "MinGW rating"),
    ("n", "mingw_reviews", 171, "MinGW review count"),
    ("n", "npp_rating", "4.4", "Notepad++ Plugin Manager rating"),
    ("n", "npp_reviews", 64, "Notepad++ Plugin Manager review count"),
    ("p", "sz_updated", "2026-09-04"),
    ("n", "sz_total_reviews", 831, "7-Zip total review count on its project page"),
    ("n", "sz_rating", "4.8", "7-Zip rating from its Reviews page"),
]

TASKS[6] = [
    ("path", "visited_crm", r"/software/crm/"),
    ("path", "visited_pipedrive", r"/software/product/Pipedrive/"),
    ("path", "visited_suitecrm", r"/software/product/SuiteCRM/"),
    ("path", "visited_espocrm", r"/software/product/EspoCRM/"),
    ("path", "crm_search_sorted", r"/directory/\?q=CRM.*sort=rating"),
    ("path", "visited_dolibarr", r"/projects/dolibarr/"),
    ("path", "visited_dolibarr_reviews", r"/projects/dolibarr/reviews/"),
    ("path", "visited_dolibarr_support", r"/projects/dolibarr/support"),
    ("p", "product_pipedrive", "Pipedrive"),
    ("p", "product_suitecrm", "SuiteCRM"),
    ("p", "product_espocrm", "EspoCRM"),
    ("p", "pipedrive_ratings", "3,120"),
    ("p", "pipedrive_rating_value", "4.4"),
    ("p", "suitecrm_ratings", "1,150"),
    ("p", "espocrm_ratings", "480"),
    ("p", "pipedrive_description", "easy-to-use CRM built for sales teams"),
    ("p", "category_label", "CRM"),
    ("n", "crm_results", 2, "CRM search result count"),
    ("p", "dolibarr_summary", "Open source ERP and CRM web software for business"),
    ("p", "dolibarr_license", "GPLv3"),
    ("n", "dolibarr_week", 2932, "Dolibarr weekly downloads"),
    ("p", "dolibarr_updated", "2026-05-26"),
    ("n", "dolibarr_rating", "4.8", "Dolibarr rating"),
    ("n", "dolibarr_reviews", 52, "Dolibarr review count"),
    ("p", "dolibarr_support_rec", "discussion forums"),
]

TASKS[7] = [
    ("path", "login_page", r"/auth/"),
    ("path", "search_results", r"/directory/\?q=password\+manager"),
    ("path", "visited_passwordsafe", r"/projects/passwordsafe/"),
    ("path", "visited_review_form", r"/projects/passwordsafe/reviews/new"),
    ("path", "visited_account", r"/account/"),
    ("p", "top_result", "Password Safe"),
    ("n", "top_week", 1788, "Password Safe weekly downloads"),
    ("p", "review_text_daily", "daily"),
    ("state", None),
]

TASKS[8] = [
    ("path", "visited_stats_timeline", r"/stats/timeline"),
    ("path", "visited_stats_os", r"/stats/os"),
    ("path", "visited_stats_map", r"/stats/map"),
    ("path", "sorted_search", r"/directory/\?q=file(\+|%20)compression.*sort=popular"),
    ("path", "visited_mingw", r"/projects/mingw/"),
    ("path", "visited_autoclicker", r"/projects/orphamielautoclicker/"),
    ("path", "visited_winscp", r"/projects/winscp/"),
    ("p", "top_country", "United States"),
    ("n", "top_country_count", "40,718", "US downloads"),
    ("p", "top_os", "Windows"),
    ("n", "top_os_count", "90,456", "Windows downloads"),
    ("p", "peak_day", "2026-09-19"),
    ("n", "peak_day_count", "6,001", "highest-day downloads"),
    ("p", "mingw_reg", "2000-02-09"),
    ("p", "mingw_license", "GPLv3"),
    ("p", "auto_reg", "2014-06-19"),
    ("p", "auto_license", "Creative Commons Attribution Non-Commercial"),
    ("p", "winscp_reg", "2003-07-13"),
    ("p", "winscp_license", "GPLv2"),
    ("p", "most_recent_updated", "WinSCP"),
    ("p", "most_recent_date", "2026-09-03"),
]

TASKS[9] = [
    ("path", "visited_games", r"/directory/games/"),
    ("path", "visited_games_page2", r"/directory/games/.*page=2"),
    ("path", "visited_dosbox", r"/projects/dosbox/"),
    ("path", "visited_dosbox_reviews", r"/projects/dosbox/reviews/"),
    ("path", "visited_dosbox_support", r"/projects/dosbox/support"),
    ("path", "visited_neko", r"/projects/neko-void/"),
    ("path", "visited_neko_reviews", r"/projects/neko-void/reviews/"),
    ("path", "visited_top", r"/top"),
    ("n", "games_count", 26, "games project count"),
    ("p", "first_project", "DOSBox"),
    ("p", "second_project", "Neko Void"),
    ("p", "page2_first", "ii's Stupid Menu"),
    ("p", "first_license", "GNU General Public License version 2.0"),
    ("p", "first_updated", "2025-08-25"),
    ("n", "first_week", "14,848", "DOSBox weekly downloads"),
    ("n", "first_rating", "4.7", "DOSBox rating"),
    ("n", "first_reviews", 165, "DOSBox review count"),
    ("p", "first_support_rec", "discussion forums"),
    ("p", "second_license", "GPLv3"),
    ("p", "second_updated", "2026-08-31"),
    ("n", "second_week", "9,044", "Neko Void weekly downloads"),
    ("n", "second_rating", "4.5", "Neko Void rating"),
    ("n", "second_reviews", 4, "Neko Void review count"),
    ("p", "weekly_no1", "MinGW"),
]

TASKS[10] = [
    ("path", "visited_homepage", r"localhost:\d+/?$"),
    ("path", "visited_portableapps", r"/projects/portableapps/"),
    ("path", "visited_pp_reviews", r"/projects/portableapps/reviews/"),
    ("path", "visited_7zip", r"/projects/sevenzip/"),
    ("path", "visited_sz_reviews", r"/projects/sevenzip/reviews/"),
    ("path", "visited_keepass", r"/projects/keepass/"),
    ("path", "visited_kp_reviews", r"/projects/keepass/reviews/"),
    ("path", "visited_top", r"/top"),
    ("p", "staff_choice", "7-Zip"),
    ("p", "community_choice", "KeePass"),
    ("n", "staff_reviews", 831, "7-Zip review count"),
    ("n", "community_reviews", 606, "KeePass review count"),
    ("p", "portable_platform", "PortableApps.com"),
    ("n", "portable_week", "422,400", "PortableApps.com weekly downloads"),
    ("p", "portable_registered", "2005-10-21"),
    ("p", "portable_license", "MPL 1.1"),
    ("n", "portable_rating", "4.9", "PortableApps.com rating"),
    ("n", "portable_reviews", 266, "PortableApps.com review count"),
    ("n", "sz_week", 23587, "7-Zip weekly downloads"),
    ("p", "sz_updated", "2026-09-04"),
    ("n", "sz_rating", "4.8", "7-Zip rating"),
    ("n", "sz_five_star", 765, "7-Zip 5-star count"),
    ("n", "sz_one_star", 27, "7-Zip 1-star count"),
    ("n", "kp_week", "205,800", "KeePass weekly downloads"),
    ("p", "kp_updated", "2026-07-25"),
    ("n", "kp_rating", "4.9", "KeePass rating"),
    ("p", "weekly_no1", "MinGW"),
]

TASKS[11] = [
    ("path", "search_results", r"/directory/\?q=video\+player"),
    ("path", "visited_next_player", r"/projects/next-player/"),
    ("path", "visited_videojs", r"/projects/video-js/"),
    ("path", "windows_facet", r"/directory/windows/"),
    ("path", "visited_mpv", r"/projects/mpv-player-windows/"),
    ("path", "visited_mpv_reviews", r"/projects/mpv-player-windows/reviews/"),
    ("path", "windows_sorted_rating", r"/directory/windows/.*sort=rating"),
    ("n", "total_results", 53, "video player results"),
    ("p", "android_native", "Next Player"),
    ("n", "android_week", 37, "Next Player weekly downloads"),
    ("p", "android_updated", "2026-08-09"),
    ("p", "html5_player", "Video.js"),
    ("p", "videojs_updated", "2026-08-10"),
    ("n", "windows_count", 13, "windows-only result count"),
    ("p", "windows_first", "mpv player (Windows)"),
    ("n", "windows_first_week", "9,572", "mpv player (Windows) weekly downloads"),
    ("p", "windows_first_reg", "2015-12-31"),
    ("n", "windows_first_rating", "4.3", "mpv player (Windows) rating"),
    ("p", "rating_sort_first", "Shotcut"),
]

TASKS[12] = [
    ("path", "visited_7zip", r"/projects/sevenzip/"),
    ("path", "visited_profile", r"/u/ipavlov/profile/"),
    ("path", "visited_p7zip", r"/projects/p7zip/"),
    ("path", "visited_7max", r"/projects/sevenmax/"),
    ("path", "visited_7far", r"/projects/sevenfar/"),
    ("path", "visited_sz_reviews", r"/projects/sevenzip/reviews/"),
    ("path", "visited_1star_filter", r"/projects/sevenzip/reviews/.*filter-stars=1"),
    ("path", "visited_4star_filter", r"/projects/sevenzip/reviews/.*filter-stars=4"),
    ("p", "username", "ipavlov"),
    ("p", "display_name", "Igor Pavlov"),
    ("p", "join_date", "2000-08-17"),
    ("p", "project_7zip", "7-Zip"),
    ("p", "project_p7zip", "p7zip"),
    ("p", "project_7far", "7-Far"),
    ("p", "project_7max", "7-max"),
    ("p", "p7zip_summary", "Command-line port of the 7-Zip file archiver"),
    ("p", "p7zip_license", "GNU Library or Lesser General Public License version 2.0"),
    ("p", "p7zip_reg", "2004-06-12"),
    ("p", "max_summary", "speeds up Windows applications by optimising memory allocation"),
    ("p", "max_license", "GNU Library or Lesser General Public License version 2.0"),
    ("p", "max_reg", "2004-08-12"),
    ("p", "far_summary", "7-Zip archiver plugin for the FAR Manager file manager"),
    ("p", "far_license", "GNU Library or Lesser General Public License version 2.0"),
    ("p", "far_reg", "2009-12-28"),
    ("n", "sz_rating", "4.8", "7-Zip rating"),
    ("n", "one_star_view", 3, "reviews in the 1-star filter view"),
    ("n", "four_star_view", 6, "reviews in the 4-star filter view"),
    ("n", "sz_total_reviews", 831, "7-Zip total review count on its project page"),
]

TASKS[13] = [
    ("path", "visited_registration", r"/user/registration/"),
    ("path", "visited_account_edit", r"/account/edit"),
    ("path", "visited_account", r"/account/"),
    ("path", "visited_crystaldiskinfo", r"/projects/crystaldiskinfo/"),
    ("p", "username_registered", "fleet-admin"),
    ("p", "country_germany", "Germany"),
    ("p", "display_name_set", "Fleet"),
    ("p", "bookmark_crystaldiskinfo", "CrystalDiskInfo"),
    ("p", "account_heading", "My Account"),
    ("p", "edit_heading", "Edit Profile"),
    ("p", "no_reviews_wording", "any reviews yet"),
    ("state", None),
]

TASKS[14] = [
    ("path", "visited_wiki", r"/p/sevenzip/wiki/"),
    ("path", "visited_news", r"/p/sevenzip/news/"),
    ("path", "visited_support", r"/projects/sevenzip/support"),
    ("path", "visited_forum", r"/p/sevenzip/discussion/45797/"),
    ("path", "visited_highview_thread", r"/thread/b8d64839d0/"),
    ("path", "visited_help_forum", r"/p/sevenzip/discussion/45798/"),
    ("p", "wiki_format_7z", "7z"),
    ("p", "wiki_format_zip", "ZIP"),
    ("p", "wiki_format_gzip", "GZIP"),
    ("p", "wiki_author", "Igor Pavlov"),
    ("p", "wiki_last_modified", "2026-09-04"),
    ("p", "news_title_1", "7-Zip 9.21 beta"),
    ("p", "news_date_1", "2011-04-15"),
    ("p", "news_title_2", "7-Zip 9.20 was released"),
    ("p", "news_date_2", "2010-11-25"),
    ("p", "support_forum_rec", "45797"),
    ("p", "max_views_thread", "7-Zip 26.02"),
    ("n", "max_views", "297,148", "highest-view thread view count"),
    ("p", "help_forum_name", "Help"),
    ("any", "help_topic_count", ["25", "8,276", "8276"], "topics the Help forum lists"),
    ("p", "help_hv_subject", "Compress multiple files to individual ZIP archives with fixed size"),
    ("p", "help_hv_creator", "rtm"),
]

TASKS[15] = [
    ("path", "visited_cve_search", r"/p/sevenzip/bugs/search/.*CVE"),
    ("path", "visited_ticket_2681", r"/p/sevenzip/bugs/2681/"),
    ("path", "visited_ticket_2670", r"/p/sevenzip/bugs/2670/"),
    ("path", "visited_ticket_2669", r"/p/sevenzip/bugs/2669/"),
    ("path", "visited_forum", r"/p/sevenzip/discussion/45797/"),
    ("n", "cve_ticket_count", 3, "CVE search results"),
    ("p", "cve_newest_1", "2681"),
    ("p", "cve_newest_1_summary", "CVE-2026-58052"),
    ("p", "cve_newest_2", "2670"),
    ("p", "cve_newest_2_summary", "CVE-2026-48102"),
    ("p", "ticket_status_open", "open"),
    ("n", "cve_newest_1_priority", 7, "ticket 2681 priority"),
    ("n", "cve_newest_2_priority", 7, "ticket 2670 priority"),
    ("p", "cve_lowest", "2669"),
    ("p", "cve_lowest_owner", "Igor Pavlov"),
    ("p", "cve_lowest_created", "2026-06-10"),
    ("p", "vuln_thread_subject", "vulnerability scanner flagged version 26.02 as unsafe"),
    ("p", "vuln_thread_creator", "Robert Barcikowski"),
    ("n", "vuln_thread_posts", 7, "vulnerability thread post count"),
    ("n", "open_tickets", 31, "open ticket count"),
]

TASKS[16] = [
    ("path", "visited_sdk_folder", r"/projects/sevenzip/files/LZMA(%20|\+)SDK/"),
    ("path", "visited_sdk_download", r"lzma2601\.7z/download"),
    ("path", "visited_2601_folder", r"/projects/sevenzip/files/7-Zip/26\.01/"),
    ("path", "visited_2600_folder", r"/projects/sevenzip/files/7-Zip/26\.00/"),
    ("path", "visited_2600_download", r"7z2600-x64\.exe/download"),
    ("p", "file_2601", "lzma2601.7z"),
    ("p", "file_2600", "lzma2600.7z"),
    ("p", "file_2409", "lzma2409.7z"),
    ("p", "file_2408", "lzma2408.7z"),
    ("p", "size_2601", "1.8 MB"),
    ("p", "modified_2601", "2026-04-29"),
    ("n", "newest_week", 27, "lzma2601.7z weekly downloads"),
    ("n", "sdk_folder_week", 675, "LZMA SDK folder weekly downloads"),
    ("p", "build_2601_x64", "7z2601-x64.exe"),
    ("n", "build_2601_x64_week", "5,494", "7z2601-x64.exe weekly downloads"),
    ("p", "build_2601_msi", "7z2601-x64.msi"),
    ("n", "build_2601_msi_week", "1,210", "7z2601-x64.msi weekly downloads"),
    ("p", "build_2600_x64", "7z2600-x64.exe"),
    ("n", "build_2600_x64_week", "2,038", "7z2600-x64.exe weekly downloads"),
    ("n", "root_folder_week", 23345, "7-Zip root folder weekly downloads"),
]

TASKS[17] = [
    ("path", "visited_keepass", r"/projects/keepass/"),
    ("path", "visited_kp_reviews", r"/projects/keepass/reviews/"),
    ("path", "visited_kp_support", r"/projects/keepass/support"),
    ("path", "visited_7zip", r"/projects/sevenzip/"),
    ("path", "visited_sz_reviews", r"/projects/sevenzip/reviews/"),
    ("path", "visited_sz_support", r"/projects/sevenzip/support"),
    ("path", "visited_forum", r"/p/sevenzip/discussion/"),
    ("path", "visited_top", r"/top"),
    ("n", "kp_week", "205,800", "KeePass weekly downloads"),
    ("n", "kp_reviews", 606, "KeePass review count"),
    ("p", "kp_registered", "2003-11-15"),
    ("n", "kp_rating", "4.9", "KeePass rating"),
    ("n", "kp_five_star", 567, "KeePass 5-star count"),
    ("n", "kp_one_star", 11, "KeePass 1-star count"),
    ("p", "kp_support_rec", "discussion forums"),
    ("n", "sz_week", 23587, "7-Zip weekly downloads"),
    ("n", "sz_reviews", 831, "7-Zip review count"),
    ("p", "sz_registered", "2000-11-10"),
    ("n", "sz_rating", "4.8", "7-Zip rating"),
    ("n", "sz_five_star", 765, "7-Zip 5-star count"),
    ("n", "sz_one_star", 27, "7-Zip 1-star count"),
    ("p", "sz_support_rec", "45797"),
    ("p", "forum_name", "Open Discussion"),
    ("n", "forum_topics", "29,076", "Open Discussion topic count"),
    ("p", "sz_total_larger", "430M"),
    ("p", "kp_total", "191M"),
]

TASKS[18] = [
    ("path", "login_page", r"/auth/"),
    ("path", "visited_account", r"/account/"),
    ("path", "visited_crystaldiskinfo", r"/projects/crystaldiskinfo/"),
    ("path", "visited_ventoy", r"/projects/ventoy/"),
    ("path", "visited_review_form", r"/projects/ventoy/reviews/new"),
    ("p", "bookmark_winscp", "WinSCP"),
    ("p", "bookmark_before_crystaldiskinfo", "CrystalDiskInfo"),
    ("p", "bookmark_after_ventoy", "Ventoy"),
    ("p", "review_mentions_usb", "USB"),
    ("state", None),
]

TASKS[19] = [
    ("path", "visited_about", r"/about"),
    ("path", "visited_leadership", r"/about/leadership"),
    ("path", "visited_podcast", r"/podcast/"),
    ("path", "visited_articles", r"/articles/"),
    ("path", "visited_case_studies", r"/software/case-studies/"),
    ("path", "visited_ninjaone", r"/software/product/NinjaOne/"),
    ("path", "visited_gcp", r"/software/product/Google-Cloud-Platform/"),
    ("path", "visited_blog", r"/blog/"),
    ("path", "visited_vendors", r"/software/vendors/"),
    ("path", "visited_create", r"/create"),
    ("path", "visited_support", r"/support"),
    ("path", "visited_file_compression_search", r"/directory/.*file.compression"),
    ("p", "founded_1999", "1999"),
    ("p", "software_titles", "123,200"),
    ("p", "leader_1", "Logan Abbott"),
    ("p", "leader_1_title", "President, SourceForge"),
    ("p", "leader_2", "Roger Sheppard"),
    ("p", "leader_2_title", "President of Slashdot Media"),
    ("p", "podcast_episode", "FastField"),
    ("p", "podcast_episode_number", "#138"),
    ("p", "podcast_date", "2026-09-03"),
    ("p", "newest_article", "Trend Analysis and Capacity Planning"),
    ("p", "article_date", "2026-09-03"),
    ("p", "vendor_1", "Gemini Enterprise Agent Platform"),
    ("p", "vendor_2", "Google Cloud Platform"),
    ("p", "vendor_3", "NinjaOne"),
    ("n", "ninjaone_ratings", "6,035", "NinjaOne ratings count"),
    ("n", "gcp_ratings", "61,049", "Google Cloud Platform ratings count"),
    ("p", "newest_blog_post", "Trend Analysis and Capacity Planning"),
    ("p", "blog_date", "2026-09-03"),
    ("p", "vendors_offer", "list your product in the Business Software directory"),
    ("p", "create_invite", "Find, Create & Publish Open Source software for free"),
    ("p", "support_fastest", "fastest way to get help"),
    ("p", "hq_address", "1320 Columbia Street Suite 310"),
    ("p", "hq_city", "San Diego"),
    ("n", "file_compression_count", 96, "projects returned by the 'file compression' directory search"),
]

TASKS[20] = [
    ("path", "visited_erp", r"/software/erp/"),
    ("path", "visited_odoo", r"/software/product/Odoo/"),
    ("path", "visited_dolibarr_biz", r"/software/product/Dolibarr/"),
    ("path", "erp_search_sorted", r"/directory/\?q=erp.*sort=rating"),
    ("path", "visited_dolibarr", r"/projects/dolibarr/"),
    ("path", "visited_dolibarr_reviews", r"/projects/dolibarr/reviews/"),
    ("path", "visited_dolibarr_support", r"/projects/dolibarr/support"),
    ("path", "visited_pseint", r"/projects/pseint/"),
    ("p", "product_odoo", "Odoo"),
    ("p", "product_dolibarr", "Dolibarr"),
    ("p", "odoo_rating", "4.3"),
    ("p", "odoo_ratings_count", "4,100"),
    ("p", "dolibarr_rating", "4.2"),
    ("p", "dolibarr_ratings_count", "940"),
    ("p", "odoo_description", "suite of open source business apps"),
    ("p", "dolibarr_biz_description", "Open source ERP and CRM web software for business"),
    ("n", "erp_results", 8, "erp search result count"),
    ("p", "dolibarr_summary", "Open source ERP and CRM web software for business"),
    ("p", "dolibarr_license", "GPLv3"),
    ("n", "dolibarr_week", 2932, "Dolibarr weekly downloads"),
    ("p", "dolibarr_updated", "2026-05-26"),
    ("p", "dolibarr_reg", "2005-11-28"),
    ("n", "dolibarr_rating_avg", "4.8", "Dolibarr average rating"),
    ("n", "dolibarr_reviews", 52, "Dolibarr review count"),
    ("p", "dolibarr_support_rec", "discussion forums"),
    ("p", "pseint_reg", "2004-11-28"),
]

# stateful DB-delta check bodies
STATE_7 = '''    # stateful: alice bookmarked Password Safe and posted it a 5-star review.
    check_only_tables_changed(judge, initial_db, after_db, {"bookmarks", "reviews", "projects"})
    added, removed, changed = table_diff(initial_db, after_db, "bookmarks")
    judge.check("bookmark_added_passwordsafe",
                len(added) == 1 and added and all(r["project_id"] == _pid(after_db, "passwordsafe") and r["user_id"] == 1991 for r in added.values()) and not removed and not changed,
                f"added={list(added.values())} removed={list(removed.values())} changed={list(changed.values())[:2]}")
    added, removed, changed = table_diff(initial_db, after_db, "reviews")
    ok_rev = (len(added) == 1 and not removed)
    if ok_rev:
        row = list(added.values())[0]
        ok_rev = (row["author_name"] == "alice_j" and row["rating"] == 5
                  and "daily" in (row["text"] or ""))
    judge.check("review_added_5star_daily", ok_rev,
                f"added={list(added.values())} removed={list(removed.values())}")
    added, removed, changed = table_diff(initial_db, after_db, "projects")
    ok_p = len(changed) == 1 and not added and not removed
    if ok_p:
        old, new = list(changed.values())[0]
        ok_p = (new["review_count"] == old["review_count"] + 1
                and new["stars_5"] == old["stars_5"] + 1
                and new["shortname"] == "passwordsafe")
    judge.check("passwordsafe_counters_bumped", ok_p,
                f"changed={[(c, v[1]['shortname']) for c, v in changed.items()]}")
'''

STATE_13 = '''    # stateful: fleet-admin registered (country DE, display name set) and
    # bookmarked CrystalDiskInfo.
    check_only_tables_changed(judge, initial_db, after_db, {"users", "bookmarks"})
    added, removed, changed = table_diff(initial_db, after_db, "users")
    ok_u = len(added) == 1 and not removed and not changed
    if ok_u:
        row = list(added.values())[0]
        ok_u = (row["username"] == "fleet-admin"
                and row["email"] == "fleet-admin@example.com"
                and row["country"] == "DE"
                and (row["display_name"] or "") != "")
    judge.check("user_registered_de_display_name", ok_u,
                f"added={list(added.values())} removed={list(removed.values())} changed={list(changed.values())[:2]}")
    added, removed, changed = table_diff(initial_db, after_db, "bookmarks")
    ok_b = len(added) == 1 and not removed and not changed
    if ok_b:
        row = list(added.values())[0]
        ok_b = (row["project_id"] == _pid(after_db, "crystaldiskinfo")
                and row["user_id"] == list(table_diff(initial_db, after_db, "users")[0].values())[0]["id"])
    judge.check("bookmark_added_crystaldiskinfo", ok_b,
                f"added={list(added.values())} removed={list(removed.values())} changed={list(changed.values())[:2]}")
'''

STATE_18 = '''    # stateful: bob removed CrystalDiskInfo, added Ventoy, posted a 4-star review.
    check_only_tables_changed(judge, initial_db, after_db, {"bookmarks", "reviews", "projects"})
    added, removed, changed = table_diff(initial_db, after_db, "bookmarks")
    ok_b = False
    delta = {"added": list(added.values()), "removed": list(removed.values()),
             "changed": [(k, v[0]["project_id"], v[1]["project_id"]) for k, v in changed.items()]}
    if len(changed) == 1 and not added and not removed:
        (old_row, new_row) = list(changed.values())[0]
        ok_b = (new_row["user_id"] == 1992
                and new_row["project_id"] == _pid(after_db, "ventoy")
                and old_row["project_id"] == _pid(initial_db, "crystaldiskinfo"))
    elif len(added) == 1 and len(removed) == 1 and not changed:
        ok_b = (all(r["project_id"] == _pid(after_db, "ventoy") and r["user_id"] == 1992 for r in added.values())
                and all(r["project_id"] == _pid(initial_db, "crystaldiskinfo") and r["user_id"] == 1992 for r in removed.values()))
    judge.check("bookmark_swap_ventoy_for_crystaldiskinfo", ok_b,
                f"delta={delta}")
    added, removed, changed = table_diff(initial_db, after_db, "reviews")
    ok_rev = (len(added) == 1 and not removed)
    if ok_rev:
        row = list(added.values())[0]
        ok_rev = (row["author_name"] == "bob_c" and row["rating"] == 4
                  and "usb" in (row["text"] or "").lower())
    judge.check("review_added_4star_usb", ok_rev,
                f"added={list(added.values())} removed={list(removed.values())}")
    added, removed, changed = table_diff(initial_db, after_db, "projects")
    ok_p = len(changed) == 1 and not added and not removed
    if ok_p:
        old, new = list(changed.values())[0]
        ok_p = (new["review_count"] == old["review_count"] + 1
                and new["stars_4"] == old["stars_4"] + 1
                and new["shortname"] == "ventoy")
    judge.check("ventoy_counters_bumped", ok_p,
                f"changed={[(c, v[1]['shortname']) for c, v in changed.items()]}")
'''

HELPER = '''

def _pid(db, shortname):
    return db.execute("SELECT id FROM projects WHERE shortname = ?", (shortname,)).fetchone()[0]
'''

# Subject binding for every numeric fact. A number counts only when the nearest
# preceding subject (else a short following subject) is the expected one, so a
# swapped attribution fails even though every integer still appears somewhere.
# `near` / `context` disambiguate two facts about the same subject (histogram
# vs filter count, priority vs post count, the same date on three pages).
_PROJ = ("MinGW", "AutoClicker", "7-Zip")
_TOP3 = ("corefonts", "MinGW", "Notepad++ Plugin Manager", "7-Zip")
_FILES = ("lzma2408.7z", "lzma2409.7z", "lzma2600.7z", "lzma2601.7z",
          "7z2601-x64.exe", "7z2601-x64.msi", "7z2600-x64.exe")
# First histogram bucket: "5-star 765", "stars ['765'", or "histogram ['567'".
_HIST5 = (r"5[\-\s]?stars?", r"stars\s*\[\s*'?", r"histogram\s*\[\s*'?")
_HIST1 = (r"1[\-\s]?stars?", r"'\s*\]")

def _others(name, group):
    return tuple(item for item in group if item != name)


BIND = {}
PHRASE_BIND = {}

def _n(task, name, spec):
    BIND[(task, name)] = spec

def _p(task, name, spec):
    PHRASE_BIND[(task, name)] = spec

# --- task 0 ---
for _name, _subj, _near in (
    ("mingw_week", "MinGW", r"weekly"),
    ("mingw_rating", "MinGW", r"rating"),
    ("mingw_reviews", "MinGW", r"reviews?"),
    ("auto_week", "AutoClicker", r"weekly"),
    ("auto_rating", "AutoClicker", r"rating"),
    ("auto_reviews", "AutoClicker", r"reviews?"),
    ("sz_week", "7-Zip", r"weekly"),
    ("sz_rating", "7-Zip", r"rating"),
    ("sz_reviews", "7-Zip", r"reviews?"),
):
    _n(0, _name, B(_subj, *_others(_subj, _PROJ), near=_near))
_p(0, "mingw_reg", B("MinGW", "AutoClicker", "7-Zip"))
_p(0, "auto_reg", B("AutoClicker", "MinGW", "7-Zip"))
_p(0, "sz_reg", B("7-Zip", "MinGW", "AutoClicker"))
_p(0, "mingw_license", B("MinGW", "AutoClicker", "7-Zip", near=r"licen"))
_p(0, "auto_license", B("AutoClicker", "MinGW", "7-Zip", near=r"licen"))
_p(0, "sz_license", B("7-Zip", "MinGW", "AutoClicker", near=r"licen"))
_p(0, "sz_updated_more_recent", B("7-Zip", "MinGW", "AutoClicker", near=r"updat|recent"))

# --- task 1 ---
_n(1, "folder_week_2603", B("26.03", "26.02", near=r"weekly|="))
_n(1, "folder_week_2602", B("26.02", "26.03", near=r"weekly|="))
_n(1, "peak_day_count", B("peak", "Windows", "26.03", "26.02", near=r"day|download"))
_n(1, "top_os_count", B("Windows", "peak", "26.03", "26.02", near=r"download"))
_p(1, "peak_day", B("peak", "Windows", near=r"day"))

# --- task 2 ---
_n(2, "sz_avg", B("7-Zip", "KeePass", near=r"rating"))
_n(2, "sz_five_star", B("7-Zip", "KeePass", context=_HIST5, context_window=24))
_n(2, "sz_one_star", B("7-Zip", "KeePass", context=_HIST1, context_window=16))
_n(2, "sz_four_star_view", B("7-Zip", "KeePass", near=r"4[\-\s]?stars?"))
_n(2, "kp_avg", B("KeePass", "7-Zip", near=r"rating"))
_n(2, "kp_five_star", B("KeePass", "7-Zip", context=_HIST5, context_window=24))
_n(2, "kp_one_star", B("KeePass", "7-Zip", context=_HIST1, context_window=16))
_n(2, "kp_five_star_view", B("KeePass", "7-Zip", near=r"5[\-\s]?stars?"))
_n(2, "kp_four_star_view", B("KeePass", "7-Zip", near=r"4[\-\s]?stars?"))
_n(2, "sz_total_reviews", B("7-Zip", "KeePass", context=(r"831\s*vs",), context_window=12))
_n(2, "kp_total_reviews", B("7-Zip", "KeePass", context=(r"vs\s*606",), context_window=12))

# --- task 3 ---
_CVE = ("2701", "2681", "2670", "2669")
_n(3, "ticket_priority", B("2701", *_others("2701", _CVE), near=r"priorit"))
_n(3, "cve_ticket_count", B("CVE", *_CVE, near=r"return|ticket"))
_n(3, "cve_newest_1_priority", B("2681", *_others("2681", _CVE), near=r"priorit"))
_n(3, "cve_newest_2_priority", B("2670", *_others("2670", _CVE), near=r"priorit"))
_n(3, "open_tickets", B("sidebar", *_CVE, near=r"open"))
_p(3, "ticket_status_open", B("2701", *_others("2701", _CVE), near=r"status"))
_p(3, "cve_newest_1", B("CVE-2026-58052", "CVE-2026-48102", "2669"))
_p(3, "cve_newest_2", B("CVE-2026-48102", "CVE-2026-58052", "2669"))
_p(3, "cve_lowest", B("2669", "2681", "2670", near=r"own|creat|Igor"))
_p(3, "cve_lowest_created", B("2669", "2681", "2670"))

# --- task 4 ---
_THREADS = ("Dark Mode", "Dark Theme", "7-Zip 26.02", "Help", "rtm")
_n(4, "thread_posts", B("Dark Mode", *_others("Dark Mode", _THREADS), near=r"posts?"))
_n(4, "thread_views", B("Dark Mode", *_others("Dark Mode", _THREADS), near=r"views?"))
_n(4, "darktheme_posts", B("Dark Theme", *_others("Dark Theme", _THREADS), near=r"posts?"))
_n(4, "darktheme_views", B("Dark Theme", *_others("Dark Theme", _THREADS), near=r"views?"))
_n(4, "max_views", B("7-Zip 26.02", *_others("7-Zip 26.02", _THREADS), near=r"views?"))
_n(4, "help_topic_count", B("Help", *_others("Help", _THREADS), near=r"topics?"))
_n(4, "help_hv_views", B("rtm", *_others("rtm", _THREADS), near=r"views?"))
_p(4, "thread_created", B("Dark Mode", "Dark Theme", "Help"))

# --- task 5 ---
for _name, _subj, _near in (
    ("corefonts_week", "corefonts", r"weekly"),
    ("mingw_week", "MinGW", r"weekly"),
    ("npp_week", "Notepad++ Plugin Manager", r"weekly"),
    ("corefonts_rating", "corefonts", r"rating"),
    ("corefonts_reviews", "corefonts", r"reviews?"),
    ("mingw_rating", "MinGW", r"rating"),
    ("mingw_reviews", "MinGW", r"reviews?"),
    ("npp_rating", "Notepad++ Plugin Manager", r"rating"),
    ("npp_reviews", "Notepad++ Plugin Manager", r"reviews?"),
    ("sz_total_reviews", "7-Zip", r"total|reviews"),
    ("sz_rating", "7-Zip", r"rating"),
):
    _n(5, _name, B(_subj, *_others(_subj, _TOP3), near=_near))
_n(5, "sz_alltime_rank", B("7-Zip", *_others("7-Zip", _TOP3), near=r"all-time|rank|#"))
_n(5, "sz_alltime_total", B("7-Zip", *_others("7-Zip", _TOP3), near=r"430|all-time|total"))
_p(5, "alltime_no1_downloads", B("TrueType", "MinGW", "7-Zip"))
_p(5, "weekly_no1_downloads", B("MinGW", "TrueType", "7-Zip"))
_p(5, "corefonts_reg", B("corefonts", *_others("corefonts", _TOP3)))
_p(5, "mingw_reg", B("MinGW", *_others("MinGW", _TOP3)))
_p(5, "npp_reg", B("Notepad++ Plugin Manager", *_others("Notepad++ Plugin Manager", _TOP3)))
_p(5, "corefonts_license", B("corefonts", *_others("corefonts", _TOP3), near=r"licen"))
_p(5, "mingw_license", B("MinGW", *_others("MinGW", _TOP3), near=r"licen"))
_p(5, "sz_updated", B("7-Zip", *_others("7-Zip", _TOP3), near=r"updat"))

# --- task 6 ---
_CRM = ("Pipedrive", "SuiteCRM", "EspoCRM", "Dolibarr")
_n(6, "pipedrive_ratings", B("Pipedrive", *_others("Pipedrive", _CRM), near=r"ratings?"))
_n(6, "pipedrive_rating_value", B("Pipedrive", *_others("Pipedrive", _CRM), near=r"\d"))
_n(6, "suitecrm_ratings", B("SuiteCRM", *_others("SuiteCRM", _CRM), near=r"ratings?"))
_n(6, "espocrm_ratings", B("EspoCRM", *_others("EspoCRM", _CRM), near=r"ratings?"))
_n(6, "crm_results", B("CRM", *_CRM, near=r"results?"))
_n(6, "dolibarr_week", B("Dolibarr", *_others("Dolibarr", _CRM), near=r"weekly"))
_n(6, "dolibarr_rating", B("Dolibarr", *_others("Dolibarr", _CRM), near=r"rating"))
_n(6, "dolibarr_reviews", B("Dolibarr", *_others("Dolibarr", _CRM), near=r"reviews?"))
_p(6, "dolibarr_updated", B("Dolibarr", *_others("Dolibarr", _CRM), near=r"updat"))
_p(6, "dolibarr_license", B("Dolibarr", *_others("Dolibarr", _CRM), near=r"licen"))

# --- task 7 ---
_n(7, "top_week", B("Password Safe", "KeePass", near=r"weekly"))

# --- task 8 ---
_FC = ("MinGW", "AutoClicker", "WinSCP")
_n(8, "top_country_count", B("United States", "Windows", "peak", near=r"with|download"))
_n(8, "top_os_count", B("Windows", "United States", "peak", near=r"with|download"))
_n(8, "peak_day_count", B("peak", "Windows", "United States", near=r"day|download"))
_p(8, "peak_day", B("peak", "Windows", "United States"))
_p(8, "mingw_reg", B("MinGW", *_others("MinGW", _FC)))
_p(8, "auto_reg", B("AutoClicker", *_others("AutoClicker", _FC)))
_p(8, "winscp_reg", B("WinSCP", *_others("WinSCP", _FC)))
_p(8, "mingw_license", B("MinGW", *_others("MinGW", _FC), near=r"licen"))
_p(8, "auto_license", B("AutoClicker", *_others("AutoClicker", _FC), near=r"licen"))
_p(8, "winscp_license", B("WinSCP", *_others("WinSCP", _FC), near=r"licen"))
_p(8, "most_recent_date", B("WinSCP", *_others("WinSCP", _FC), near=r"updat|recent"))

# --- task 9 ---
_GAMES = ("DOSBox", "Neko Void", "MinGW")
_n(9, "games_count", B("Games", "DOSBox", "Neko Void", near=r"projects?|lists"))
_n(9, "first_week", B("DOSBox", *_others("DOSBox", _GAMES), near=r"weekly"))
_n(9, "first_rating", B("DOSBox", *_others("DOSBox", _GAMES), near=r"rating"))
_n(9, "first_reviews", B("DOSBox", *_others("DOSBox", _GAMES), near=r"reviews?"))
_n(9, "second_week", B("Neko Void", *_others("Neko Void", _GAMES), near=r"weekly"))
_n(9, "second_rating", B("Neko Void", *_others("Neko Void", _GAMES), near=r"rating"))
_n(9, "second_reviews", B("Neko Void", *_others("Neko Void", _GAMES), near=r"reviews?"))
_p(9, "first_updated", B("DOSBox", *_others("DOSBox", _GAMES), near=r"updat"))
_p(9, "second_updated", B("Neko Void", *_others("Neko Void", _GAMES), near=r"updat"))

# --- task 10 ---
_PICKS = ("7-Zip", "KeePass", "PortableApps.com")
_n(10, "staff_reviews", B("7-Zip", *_others("7-Zip", _PICKS), near=r"reviews?"))
_n(10, "community_reviews", B("KeePass", *_others("KeePass", _PICKS), near=r"reviews?"))
_n(10, "portable_week", B("PortableApps.com", *_others("PortableApps.com", _PICKS), near=r"weekly"))
_n(10, "portable_rating", B("PortableApps.com", *_others("PortableApps.com", _PICKS), near=r"rating"))
_n(10, "portable_reviews", B("PortableApps.com", *_others("PortableApps.com", _PICKS), near=r"reviews?"))
_n(10, "sz_week", B("7-Zip", *_others("7-Zip", _PICKS), near=r"weekly"))
_n(10, "sz_rating", B("7-Zip", *_others("7-Zip", _PICKS), near=r"rating"))
_n(10, "sz_five_star", B("7-Zip", *_others("7-Zip", _PICKS), near=r"5[\-\s]?stars?", near_window=12))
_n(10, "sz_one_star", B("7-Zip", *_others("7-Zip", _PICKS), near=r"1[\-\s]?stars?", near_window=12))
_n(10, "kp_week", B("KeePass", *_others("KeePass", _PICKS), near=r"weekly"))
_n(10, "kp_rating", B("KeePass", *_others("KeePass", _PICKS), near=r"rating"))
_p(10, "portable_registered", B("PortableApps.com", *_others("PortableApps.com", _PICKS)))
_p(10, "sz_updated", B("7-Zip", *_others("7-Zip", _PICKS), near=r"updat"))
_p(10, "kp_updated", B("KeePass", *_others("KeePass", _PICKS), near=r"updat"))
_p(10, "portable_license", B("PortableApps.com", *_others("PortableApps.com", _PICKS), near=r"licen|MPL"))

# --- task 11 ---
_VID = ("Next Player", "Video.js", "mpv", "Shotcut", "Windows-only")
_n(11, "total_results", B("video player", *_VID, near=r"results?"))
_n(11, "android_week", B("Next Player", *_others("Next Player", _VID), near=r"weekly"))
_n(11, "windows_count", B("Windows-only", *_others("Windows-only", _VID), near=r"results?"))
_n(11, "windows_first_week", B("mpv", *_others("mpv", _VID), near=r"weekly"))
_n(11, "windows_first_rating", B("mpv", *_others("mpv", _VID), near=r"rating"))
_p(11, "android_updated", B("Next Player", *_others("Next Player", _VID), near=r"updat"))
_p(11, "videojs_updated", B("Video.js", *_others("Video.js", _VID), near=r"updat"))
_p(11, "windows_first_reg", B("mpv", *_others("mpv", _VID)))

# --- task 12 ---
_FAM = ("7-Zip", "p7zip", "7-max", "7-Far")
_n(12, "sz_rating", B("7-Zip", *_others("7-Zip", _FAM), near=r"rating"))
_n(12, "one_star_view", B("7-Zip", *_others("7-Zip", _FAM), near=r"1[\-\s]?stars?", near_window=36))
_n(12, "four_star_view", B("7-Zip", *_others("7-Zip", _FAM), near=r"4[\-\s]?stars?", near_window=36))
_n(12, "sz_total_reviews", B("7-Zip", *_others("7-Zip", _FAM), near=r"total|reviews"))
_p(12, "join_date", B("joined", "p7zip", "7-max", "7-Far"))
_p(12, "p7zip_reg", B("p7zip", "7-max", "7-Far", near=r"regist"))
_p(12, "max_reg", B("7-max", "p7zip", "7-Far", near=r"regist"))
_p(12, "far_reg", B("7-Far", "p7zip", "7-max", near=r"regist"))

# --- task 14 ---
_n(14, "max_views", B("7-Zip 26.02", "Help", "rtm", near=r"views?"))
_n(14, "help_topic_count", B("Help", "7-Zip 26.02", "Dark Mode", near=r"topics?"))
_p(14, "wiki_last_modified", B("Modified", "News", "9.21", near=r"2026-09-04|Modified"))
_p(14, "news_date_1", B("9.21", "9.20"))
_p(14, "news_date_2", B("9.20", "9.21"))
_p(14, "support_forum_rec", B("forum", "Wiki", "News", near=r"45797"))

# --- task 15 ---
_n(15, "cve_ticket_count", B("CVE", "2681", "2670", "2669", near=r"return|ticket"))
_n(15, "cve_newest_1_priority", B("2681", "2670", "2669", "Barcikowski", near=r"priorit"))
_n(15, "cve_newest_2_priority", B("2670", "2681", "2669", "Barcikowski", near=r"priorit"))
_n(15, "vuln_thread_posts", B("Barcikowski", "2681", "2670", "2669", near=r"posts?"))
_n(15, "open_tickets", B("sidebar", "2681", "2670", "2669", "Barcikowski", near=r"open"))
_p(15, "cve_lowest_created", B("2669", "2681", "2670"))
_p(15, "ticket_status_open", B("2681", "2670", "2669", near=r"open"))
_p(15, "cve_newest_1", B("CVE-2026-58052", "CVE-2026-48102", "2669"))
_p(15, "cve_newest_2", B("CVE-2026-48102", "CVE-2026-58052", "2669"))
_p(15, "cve_lowest", B("2669", "2681", "2670", near=r"own|creat|Igor"))

# --- task 16 ---
_n(16, "newest_week", B("lzma2601.7z", *_others("lzma2601.7z", _FILES)))
_n(16, "sdk_folder_week", B("SDK", *_FILES, near=r"weekly"))
_n(16, "build_2601_x64_week", B("7z2601-x64.exe", *_others("7z2601-x64.exe", _FILES)))
_n(16, "build_2601_msi_week", B("7z2601-x64.msi", *_others("7z2601-x64.msi", _FILES)))
_n(16, "build_2600_x64_week", B("7z2600-x64.exe", *_others("7z2600-x64.exe", _FILES)))
_n(16, "root_folder_week", B("root", "SDK", *_FILES, near=r"weekly"))
_p(16, "size_2601", B("lzma2601.7z", *_others("lzma2601.7z", _FILES)))
_p(16, "modified_2601", B("lzma2601.7z", *_others("lzma2601.7z", _FILES)))

# --- task 17 ---
_KP = ("KeePass", "7-Zip")
_n(17, "kp_week", B("KeePass", "7-Zip", near=r"weekly"))
_n(17, "kp_reviews", B("KeePass", "7-Zip", near=r"reviews?"))
_n(17, "kp_rating", B("KeePass", "7-Zip", near=r"rating"))
_n(17, "kp_five_star", B("KeePass", "7-Zip", context=_HIST5, context_window=24))
_n(17, "kp_one_star", B("KeePass", "7-Zip", context=_HIST1, context_window=16))
_n(17, "sz_week", B("7-Zip", "KeePass", near=r"weekly"))
_n(17, "sz_reviews", B("7-Zip", "KeePass", near=r"reviews?"))
_n(17, "sz_rating", B("7-Zip", "KeePass", near=r"rating"))
_n(17, "sz_five_star", B("7-Zip", "KeePass", context=_HIST5, context_window=24))
_n(17, "sz_one_star", B("7-Zip", "KeePass", context=_HIST1, context_window=16))
_n(17, "forum_topics", B("Open Discussion", "KeePass", "7-Zip", near=r"topics?"))
_p(17, "kp_registered", B("KeePass", "7-Zip"))
_p(17, "sz_registered", B("7-Zip", "KeePass"))
_p(17, "sz_support_rec", B("forum", "KeePass", "Help", near=r"45797"))
_p(17, "sz_total_larger", B("7-Zip", "KeePass"))
_p(17, "kp_total", B("KeePass", "7-Zip"))

# --- task 19 ---
_n(19, "ninjaone_ratings", B("NinjaOne", "Google Cloud Platform", "Gemini", near=r"ratings?"))
_n(19, "gcp_ratings", B("Google Cloud Platform", "NinjaOne", "Gemini", near=r"ratings?"))
_n(19, "file_compression_count", B("file compression", "NinjaOne", "podcast", near=r"projects?|return"))
_n(19, "founded_1999", B("founded", "NinjaOne", "podcast", "blog"))
_n(19, "software_titles", B("lists", "NinjaOne", "founded", "titles", near=r"123"))
_p(19, "podcast_date", B("#138", "article", "blog"))
_p(19, "article_date", B("article", "blog", "#138"))
_p(19, "blog_date", B("blog", "article", "#138"))

# --- task 20 ---
_ERP = ("Odoo", "Dolibarr", "PSeInt")
_n(20, "odoo_rating", B("Odoo", *_others("Odoo", _ERP), near=r"ratings?"))
_n(20, "odoo_ratings_count", B("Odoo", *_others("Odoo", _ERP), near=r"ratings?"))
_n(20, "dolibarr_rating", B("Dolibarr", *_others("Dolibarr", _ERP), near=r"\bratings\b"))
_n(20, "dolibarr_ratings_count", B("Dolibarr", *_others("Dolibarr", _ERP), near=r"\bratings\b"))
_n(20, "erp_results", B("erp", "Odoo", "Dolibarr", "PSeInt", near=r"results?"))
_n(20, "dolibarr_week", B("Dolibarr", *_others("Dolibarr", _ERP), near=r"weekly"))
_n(20, "dolibarr_rating_avg", B("Dolibarr", *_others("Dolibarr", _ERP), near=r"\breviews\b"))
_n(20, "dolibarr_reviews", B("Dolibarr", *_others("Dolibarr", _ERP), near=r"\breviews\b"))
_p(20, "dolibarr_updated", B("Dolibarr", *_others("Dolibarr", _ERP), near=r"updat"))
_p(20, "dolibarr_reg", B("Dolibarr", *_others("Dolibarr", _ERP), near=r"regist"))
_p(20, "pseint_reg", B("PSeInt", *_others("PSeInt", _ERP)))
_p(20, "dolibarr_license", B("Dolibarr", *_others("Dolibarr", _ERP), near=r"licen"))


_PLAIN_NUMBER = re.compile(r"\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?")
_ABBREV_NUMBER = re.compile(r"\d+(?:\.\d+)?[KMB]", re.IGNORECASE)
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def build(n):
    checks = []
    for item in TASKS[n]:
        kind = item[0]
        if kind == "p":
            name, text = item[1], item[2]
            if (n, name) in PHRASE_BIND:
                checks.append(phrase_near(name, text, PHRASE_BIND[(n, name)]))
            elif (n, name) in BIND:
                checks.append(num(name, text, text, BIND[(n, name)]))
            elif (_PLAIN_NUMBER.fullmatch(str(text).strip())
                  or _ABBREV_NUMBER.fullmatch(str(text).strip())
                  or _ISO_DATE.fullmatch(str(text).strip())):
                raise SystemExit(f"unbound numeric phrase SourceForge--{n} {name}={text!r}")
            else:
                checks.append(phrase(name, text))
        elif kind == "n":
            name, value = item[1], item[2]
            label = item[3] if len(item) > 3 else None
            if (n, name) not in BIND:
                raise SystemExit(f"unbound number SourceForge--{n} {name}={value!r}")
            checks.append(num(name, value, label, BIND[(n, name)]))
        elif kind == "any":
            name, variants = item[1], item[2]
            label = item[3] if len(item) > 3 else ""
            if (n, name) not in BIND:
                raise SystemExit(f"unbound any-of SourceForge--{n} {name}")
            checks.append(anyof(name, variants, label, BIND[(n, name)]))
        elif kind == "path":
            name, pattern = item[1], item[2]
            checks.append(path(name, pattern))
    state = ""
    if n == 7:
        state = STATE_7
    elif n == 13:
        state = STATE_13
    elif n == 18:
        state = STATE_18
    else:
        state = RO
    body = HEADER.format(n=n, question=Q[n]) + HELPER + FOOTER.format(checks="\n".join(checks), state=state)
    return body

out = Path(__file__).parent
for n in range(21):
    p = out / f"verify_{n}.py"
    p.write_text(build(n))
    print("wrote", p)
