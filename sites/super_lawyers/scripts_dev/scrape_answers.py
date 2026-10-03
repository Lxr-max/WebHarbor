"""Harvest the Super Lawyers Answers Q&A corpus
(answers.superlawyers.com): the home rails (spotlight + recently answered),
the question detail pages (question, asker location/date, the attorney
answer with the answering lawyer's identity), and the topic/state browse
structure. Output: source_data/answers/<slug>.json
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sl_browser import ANSWERS, goto_sl, launch  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SITE_DIR = HERE.parent
OUT = SITE_DIR / "source_data" / "answers"
OUT.mkdir(parents=True, exist_ok=True)

# topics to browse for questions (match our practice-area coverage)
TOPICS = ["divorce", "personal-injury-plaintiff", "criminal-defense",
          "employment-and-labor", "estate-planning-and-probate",
          "immigration", "dui-dwi", "family-law"]
QUESTIONS_PER_TOPIC = 3


def strip_tags(fragment: str) -> str:
    text = re.sub(r"<script.*?</script>", "", fragment, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return (text.replace("&amp;", "&").replace("&#39;", "'")
                .replace("&quot;", '"').replace("&nbsp;", " ").strip())


def main_content(html: str) -> str:
    i, j = html.find("<main"), html.find("</main>")
    return html[i:j] if i != -1 and j > i else html


def parse_question(page, url: str) -> dict | None:
    goto_sl(page, url)
    html = page.content()
    if "<main" not in html or "404" in page.title():
        return None
    main = main_content(html)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", main, re.S)
    if not h1:
        return None
    asked = re.search(r"Asked in ([^<]+) on ([^<]+)", main)
    answered = re.search(r"Last answered on ([^<]+)", main)
    count = re.search(r"<h2[^>]*>\s*(\d+) answers?", main)

    # answering attorney block
    answerer = {}
    prof = re.search(
        r'href="(https://profiles\.superlawyers\.com/([^/]+)/([^/]+)/lawyer/'
        r'([^/]+)/([0-9a-f-]+)\.html?)"', main)
    if "Answered by" in main:
        chunk = main[main.find("Answered by"):]
        nm = re.search(r"<h3>\s*<a[^>]*>\s*([^<]+)</a>", chunk)
        city = re.search(r"</h3>\s*<span class=\"fw-bold d-block my-2 my-xl-0\">([^<]+)</span>", chunk)
        firm = re.search(r"</span>\s*<span class=\"d-block my-2 my-xl-0\">\s*([^<]+)</span>", chunk)
        phone = re.search(r'href="tel:\+?(\d+)"[^>]*>\s*<i[^>]*></i>([\d\-]+)', chunk)
        photo = re.search(r'<img[^>]+src="(https://cdn\.superlawyers\.com[^"]+attorney_by_uuid[^"]+)"', chunk)
        answerer = {
            "name": strip_tags(nm.group(1)) if nm else None,
            "city": strip_tags(city.group(1)) if city else None,
            "firm": strip_tags(firm.group(1)) if firm else None,
            "phone": phone.group(2) if phone else None,
            "photo_url": photo.group(1) if photo else None,
            "profile_slug": prof.group(4) if prof else None,
            "profile_uuid": prof.group(5) if prof else None,
        }

    # answer body: paragraphs after the answerer block
    body = []
    ai = main.find("Answered by")
    if ai != -1:
        chunk = main[ai:]
        for m in re.finditer(r"<p[^>]*>(.*?)</p>", chunk, re.S):
            t = strip_tags(m.group(1))
            if t and len(t) > 30:
                body.append(t)
    return {
        "url": url, "question": strip_tags(h1.group(1)),
        "asked_in": strip_tags(asked.group(1)) if asked else None,
        "asked_on": strip_tags(asked.group(2)) if asked else None,
        "last_answered_on": strip_tags(answered.group(1)) if answered else None,
        "answer_count": int(count.group(1)) if count else 1,
        "answerer": answerer, "answer_body": body[:12],
    }


def main() -> None:
    pw, browser, ctx = launch()
    page = ctx.new_page()

    # home: spotlight + recent questions + topic/state rails
    goto_sl(page, f"{ANSWERS}/")
    home_html = page.content()
    home_main = main_content(home_html)
    spotlight, recent = [], []
    for m in re.finditer(
            r'<a[^>]+href="(https://answers\.superlawyers\.com/([a-z0-9-]+)/'
            r'([a-z0-9-]+)/([^/"]+)/([0-9a-f-]+)\.html?)"[^>]*>(.*?)</a>',
            home_main, re.S):
        entry = {"href": m.group(1), "topic": m.group(2),
                 "state": m.group(3), "slug": m.group(4), "uuid": m.group(5),
                 "title": strip_tags(m.group(6))}
        if entry not in recent and entry["title"]:
            recent.append(entry)

    questions: dict[str, dict] = {}
    # recent questions from home
    for entry in recent[:8]:
        if entry["href"] in questions:
            continue
        rec = parse_question(page, entry["href"])
        if rec:
            rec.update({k: entry[k] for k in ("topic", "state", "slug", "uuid")})
            questions[entry["href"]] = rec
            print(f"[home] {rec['question'][:60]}")

    # topic browse pages
    for topic in TOPICS:
        goto_sl(page, f"{ANSWERS}/{topic}/")
        html = page.content()
        main = main_content(html)
        found = 0
        for m in re.finditer(
                r'<a[^>]+href="(https://answers\.superlawyers\.com/'
                r'([a-z0-9-]+)/([a-z0-9-]+)/([^/"]+)/([0-9a-f-]+)\.html?)"'
                r'[^>]*>(.*?)</a>', main, re.S):
            href, t = m.group(1), strip_tags(m.group(6))
            if href in questions or not t or t.lower().startswith("answered by"):
                continue
            rec = parse_question(page, href)
            if rec:
                rec.update({"topic": m.group(2), "state": m.group(3),
                            "slug": m.group(4), "uuid": m.group(5)})
                questions[href] = rec
                found += 1
                print(f"[{topic}] {rec['question'][:60]}")
            if found >= QUESTIONS_PER_TOPIC:
                break

    for href, rec in questions.items():
        slug = f"{rec['topic']}__{rec['state']}__{rec['slug'][:80]}"
        (OUT / f"{slug}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    print(f"[answers] saved {len(questions)} questions")
    browser.close()
    pw.stop()


if __name__ == "__main__":
    main()
