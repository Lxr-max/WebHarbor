# PR #245: Statista review

Reviewed Raibows' Statista mirror on fork branch `review/pr245-statista` (kept commit `153440ea`, re-slotted onto main `1c1dc23f`). The site is registered at index 99, port **40099**. This pass drove the mirror in Chromium, checked every task page, and re-ran the grading suite.

**Verdict: accept the environment on this branch. Upstream merge stays blocked until Hugging Face discussion 149 is merged and `.assets-revision` pins that archive.**

## Mechanical checks: FAIL

The failure is the asset pin. Local Statista checks passed.

- [x] `python3 -m py_compile sites/statista/app.py`
- [x] `python3 scripts/check_site_registry.py` — 100 sites, `EXPOSE 8101 40000-40099`, task URLs use `http://localhost:40099/`
- [x] `python3 -m pytest sites/statista/tests sites/statista/verify/tests -q` — **281 passed**
- [x] Seed file unchanged by the browser session: `instance_seed/statista.db` md5 `7bebd894407e8411cd6456558dcf0cae`. Schema digest `e3571669825df78e1748d07ee5e3f66184ad0f9d0d277a3e85693dcaa9c139a8`. Row digest `aa83591b6022508eadb1d656cbd4f783f115e10ec450d77d5e17ffef7a3a5952`. `test_seed_idempotent_byte_identity` passed.
- [ ] Full image and control plane. Docker is installed, and `sudo docker` can reach the socket. This checkout has the Statista bundle from `refs/pr/149` and does not have the other sites' archives, so the 100-site image was not built and `/health`, `/reset`, and `/reset-all` were not exercised. Statista itself was served with `PORT=40099 python3 sites/statista/app.py`.
- [ ] HF revision. `.assets-revision` still pins `ChilleD/WebHarbor` at `5d2b17fa21067990370f8e7fc27123a1c24d7802`. That commit does not contain `statista.tar.gz`. Discussion 149 is unmerged.

## Visual fidelity: PASS

Chromium screenshots are in `/opt/cursor/artifacts/statista/`.

- [x] Homepage uses the Statista wordmark (inline SVG), blue/navy header, search, hero, topic pills, and a card grid. Title is the upstream portal title.
- [x] Header and footer links collected from the homepage (60 unique hrefs) all returned HTTP 200, including statistics, topics, reports, industries, outlook segments, pricing, contact, login, and register.
- [x] Detail charts are labeled SVG bar/line charts drawn from the harvested series (value labels such as Facebook `3,070`). Table mode renders the same series as an HTML table. Paywalled statistics show a real thumb plus the paid-account message.
- [x] No broken images on the homepage (`naturalWidth === 0` count was 0). The three thumbs that render are 100×71 chart crops.
- [x] No horizontal overflow at 1280, 1100, 768, or 390 (`scrollWidth === clientWidth`).
- [x] Search result topic titles now show the stored name once. Stored names already end in "statistics & facts"; the SERP had been appending that suffix again (`TikTok - statistics & facts - statistics & facts`). Fixed in `templates/serp.html` and rechecked in Chromium.

Recorded gap: the ten homepage trending cards are the upstream trending ids, and only three of them have a thumb file, so most of that grid is text. The catalog itself has 390 thumb files and 30 hero files, all present for rows flagged `has_thumb` / `has_hero`.

## Functional depth: PASS

Driven in Chromium against `http://127.0.0.1:40099`, then confirmed in SQLite.

- [x] Login `alice.j@test.com` / `TestPass123!` lands on `/account` as Alice Johnson, Personal Account, 5 favorites, 3 downloads.
- [x] A wrong password now flashes only `Invalid credentials...`. Empty-field messages stay on empty fields. Rechecked in Chromium after the fix (`44-bad-login-fixed.png`).
- [x] Favorite toggle on statistic 256598 persisted across reload (saved, removed, saved again).
- [x] PNG download of that statistic appears at the top of Alice's download history, dated September 26, 2026 (`MIRROR_NOW`).
- [x] Carol (`Professional`) can download report 206237; the history row is PDF.
- [x] David (`Starter`) and Alice (`Personal`) both see the premium paywall copy on statistic 379046 because this mirror has no premium data table for it. The copy says a Starter Account or higher is required, and an entitled account is told the table is absent.
- [x] Register `frank.miller@test.com` / `frank_m` / display name Frank Miller creates a Basic account, member since September 26, 2026, 0 favorites, 0 downloads. A second new account (`reviewer.qa@test.com`) logged in again after logout.
- [x] Register rejects a malformed email on the server (`Please enter a valid email address.`). Empty submit is blocked by the browser `required` check (`checkValidity()` is false).
- [x] Contact: empty server post flashes `Please fill in all fields.`; `not-an-email` flashes the valid-email error; Dana White / `dana.white@example.com` shows "Thank you — your inquiry has been received" and inserts one `inquiries` row at `2026-09-26 12:00:00`.
- [x] Search is token overlap. "average inflation rate worldwide" returns 422 results and ranks the target statistic first. "Boston Celtic players" returns 1 weak token match, so a multi-word query is not strict AND.
- [ ] Display name is shown on the account page and is not editable. No task asks for a rename.

## Task quality: PASS

Scripted Chromium walks opened each task's target pages. Answer numbers checked below were absent from the matching SERP titles and snippets. Natural queries often rank the right page first; the figures, comparisons, and account writes are on the following page or in SQLite. Ground truth stays in `sites/statista/verify/task_specs.py`. `tasks.jsonl` has `verifier_path` and a rules-only `judge_rubric` and no `answer` key (`test_tasks_jsonl_has_no_answer_key`, `test_rubrics_do_not_leak_ground_truth`).

These walks are scripted page checks, not autonomous agent runs. The secondary LLM judge was not run.

| Task | Result | Evidence |
|---|---|---|
| Statista--0 | PASS | SERP for "average inflation rate worldwide" has no `4.13` / `3.2`. Table on `/statistics/256598/?chart=table` has both. Favorite toggle persists. |
| Statista--1 | PASS | Chart SVG on `/statistics/272014/` labels Facebook `3,070` and WhatsApp `3,000`. PNG download shows up under `/account/downloads`. |
| Statista--2 | PASS | `/statistics/268173/` shows United States `32.38` and Germany `5.45`. The gap is computed from those two. |
| Statista--3 | PASS | Bob logs in. `/statistics/267233/` labels China `2,258.02`. Favorite route is the same toggle verified on 256598. |
| Statista--4 | PASS | Pricing shows Starter `$199` / month, Personal `$649` / month, Professional `$2,388` / year, report previews on Personal, full reports and API on Professional, Basic includes free statistics. Frank's new account page shows Basic, September 26, 2026, 0 favorites, 0 downloads. |
| Statista--5 | PASS | `/study/206237/` has 37 pages, 2025, `$595`, first chapters including Consumer sentiment. `/study/123559/` has 62 pages, 2026, `$495`, PPTX/PDF, first chapter Overview. |
| Statista--6 | PASS | Outlook → Mobility → ride-hailing shows `188.60`, `229.98`, users and ARPU, China. Car rentals shows `112.00` and the matching four facts. |
| Statista--7 | PASS | Register path verified (Frank and reviewer.qa). `/statistics/276629/?chart=table` contains `38.11`. |
| Statista--8 | PASS | `/statistics/501853/?chart=table` lists Counter-Strike 2 `18.97`, Dota 2 `16.47`, and the next ranks, with survey period, Worldwide, and "Total prize pool". |
| Statista--9 | PASS | APA and MLA views on 256598 include the publisher, the statista.com URL, and Aug 13, 2026. CO2 APA view includes `(April 2026)` and its URL. Survey period `01/01/1980`–`31/12/2031`, region Worldwide. |
| Statista--10 | PASS | `/topics/6077/` shows `1.99bn`, brand value `75.67`, Indonesia, Khabane Lame, and the publisher. Editor's pick `/statistics/1299829/` shows Jun 12, 2026, the April 2026 survey window, Worldwide, and "Share of population". SERP does not contain `1.99`, `75.67`, or Khabane. |
| Statista--11 | PASS | Alice's account page says Personal. Download history lists the AI market-size PNG and, before it, the social-networks XLS, 3 rows in the seed. Favorites page lists 5. Forecast `/forecasts/1474143/` value label is "billion U.S. dollars". Removing a favorite sticks after reload. |
| Statista--12 | PASS | `/statistics/578364/?chart=table` has India `480.55`, United States `181.75`, and the rest of the ranking. Those figures are absent from the SERP. |
| Statista--13 | PASS | `content_type=Reports` on "artificial intelligence" returns one result, the in-depth report. `/study/50485/` shows 295 pages, September 2025, `$1,995 USD`, first TOC entry Description. Carol can save a report favorite. |
| Statista--14 | PASS | `/statistics/256626/` shows Sub-Saharan Africa `12.48` and the European Union `2.46`, plus the survey window and Apr 15, 2026. The worldwide chart table has `4.13` and `3.2`. |
| Statista--15 | PASS | Carol downloads Consumer Trends 2026 as PDF. History then shows that PDF above the renewable-capacity PPT. The report page exposes pages, year, and price (task 5). |
| Statista--16 | PASS | Oil table `/statistics/326017/?chart=table` has Jul 21 (`91.47` / `88.5` / `84.91`), Jul 14 (`85.21` / `86.16` / `79.34`), and Apr 28 (`104.53` / `109.74` / `99.93`), survey January 6, 2020–July 21, 2026, update July 2026. Week-over-week deltas are computed. |
| Statista--17 | PASS | `/markets/` and `/markets/424/internet/` load. US users chart shows `324` and `254` (Mar 18, 2026). Shorts table has Jun 22 `1.5` and Jul 23 `2.0`. Social chart is task 1. |
| Statista--18 | PASS | Growth table shows Pinterest `67.3`, TikTok `20.0`, Reddit `17.2`, Twitter/X `-20.1`, Snapchat `0.06`. SERP snippets omit `67.3` and `20.1`. |
| Statista--19 | PASS | Anonymous and Basic views of `/statistics/379046/` say a paid account / Starter Account or higher is required to see exact figures. Update December 2025, region Worldwide. Pricing is task 4. Conversion table has Switzerland `2.4` in Q2 '26. |
| Statista--20 | PASS | David logs in. `/topics/3104/` shows global AI `617.62bn` and generative AI `63bn`. Editor's pick is forecast 1474143, which can be favorited. |
| Statista--21 | PASS | Gaming and Consumer prices are on the report pages (task 5). Contact submission for Dana White persists and the thank-you copy is shown. |
| Statista--22 | PASS | `/recent/statistics/` lists both the worldwide inflation statistic and the CO2 statistic, with dates kept off the cards. The detail pages show Aug 13, 2026 and April 2026, both Worldwide. |

## Grading contract

Each task has `sites/statista/verify/verify_N.py`, which calls `apply_spec` with the hardcoded spec in `task_specs.py`. Numbers match only as standalone tokens (commas allowed). A number must sit nearer its subject than a competing subject, so a swapped year, country, or market fails. `3` does not match inside `3.22` or `67.3`.

`sites/statista/verify/tests/test_verifiers.py` covers, for every task, an honest pass, a no-op fail, a shortcut fail, a wrong-answer fail, swapped-subject fails, and substring-number fails. Stateful tasks also fail on a missing write and on a write to the wrong row. Read-only tasks fail if the database changes. Package tampering (wrong task id, off-site URL, missing or undecodable screenshot, trajectory not done) fails closed.

## Reviewer fixes on this branch

- Port re-slot to 40099 and registry/README/EXPOSE alignment.
- Subject-bound verifiers, rules-only rubrics, regression suite.
- Regional inflation chart 256626 keeps region labels; conversion statistic 439576 stores the country table; the TikTok topic links its report.
- Contact posts persist to `inquiries`. Listing cards omit the dates and prices the tasks ask for on the detail page.
- This pass: SERP topic titles no longer repeat "statistics & facts". A wrong password no longer also flashes the empty-field errors.

## Required before upstream merge

1. Merge Hugging Face discussion 149, fetch the merged `statista.tar.gz`, and move `.assets-revision` to that immutable revision. Confirm the seed md5 and the two verifier digests against the fetched file.
2. Run the site inside the full image once the other archives are present: control-plane `/health`, `/reset/statista` byte-identical to the seed, and a homepage 200.

## Screenshots

`/opt/cursor/artifacts/statista/` — homepage at 1280/768/390, inflation table, regional inflation, TikTok topic, both outlook markets, pricing, paywall, Switzerland conversion, oil table, social chart, eSports table, APA citation, Alice account/favorites/downloads, David paywall, Carol downloads, register, contact success and validation, corrected login error, TikTok topic SERP.
