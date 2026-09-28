# Review: PR #239 — five reserved mirrors

Upstream: https://github.com/aiming-lab/WebHarbor/pull/239
Author: @hqhq1025
Contributor head: `hqhq1025/WebHarbor` `feat/reserved-five-mirrors-20260927` @ `7920869974bd82573713d9faefefb733546233d5`
Review branch: `review/pr239` on `Lxr-max/WebHarbor` (fork PR #16). Parent of the reviewer commit is the contributor commit. `git rebase 1c1dc23f5fabdaaef67c6d3bbf87bcd6915b9518` reports **Current branch review/pr239 is up to date.**

Sites, in append order after `ryanair` on main `1c1dc23f` (99 sites, last physical port `40098`):

| Site | Slug | Index | Port |
| --- | --- | --- | --- |
| Apartments.com | `apartments_com` | 99 | 40099 |
| Eventbrite | `eventbrite` | 100 | 40100 |
| Fandom | `fandom` | 101 | 40101 |
| Mayo Clinic | `mayo_clinic` | 102 | 40102 |
| SmartAsset | `smartasset` | 103 | 40103 |

90 tasks. After this review every row has exactly `web_name`, `id`, `ques`, `web`, `upstream_url`, `verifier_path`, `judge_rubric`. No `answer` key.

## Verdict

Do not merge #239 yet. The five apps are real mirrors: Chromium shows branded layouts and real photos, auth and stateful writes work, and a scoped Docker control plane resets the Hugging Face archives byte-for-byte. Merge is blocked by the unmerged asset discussion, by task rows that are knowledge shortcuts, listing leaks, or unanswerable as written, and by seed code that does not reproduce the shipped archives.

This branch keeps the contributor commit, adds `verify_N.py` + `verify_lib.py` for all 90 tasks, and four display fixes. It does not renumber ports and does not point `.assets-revision` at the open Hugging Face discussion.

## Mechanical checks

Official `./scripts/build.sh` was not run. A clean 104-site image cannot be built in this checkout: only these five `instance_seed/*.db` files exist, and the Dockerfile runs `asset_state.py verify` against pin `5d2b17fa21067990370f8e7fc27123a1c24d7802`, which does not contain these bundles.

What ran instead is a scoped image, `webharbor:pr239-five`, built from `python:3.12-slim-bookworm` and `requirements.lock` (`pip install --require-hashes`). It copies the real `site_runner.py` and `control_server.py`, and the five site trees with the Hugging Face seeds and images. `SITES` is reduced to those five names and `BASE_PORT=40099`, so container ports stay `40099`–`40103`. Host mapping: `8201:8101`, `41099–41103:40099–40103`. The scoped Dockerfile was not committed.

| Check | Result |
| --- | --- |
| Five homepages HTTP 200 (`41099`–`41103`) | PASS |
| `GET /health` with bearer token, all five `alive` and `ready` | PASS |
| Boot md5(instance) == md5(instance_seed) for all five | PASS |
| `POST /reset/<site>` then md5 match | PASS (each ~0.8s) |
| `POST /reset-all` then md5 match | PASS (1.10s) |
| Same `/reset-all` after Playwright logins, registers, favorites, watches, and saved calculations left all five instance DBs dirty | PASS (1.17s); homepages 200 again |
| Full 104-site HTTP sweep | not run (other seeds absent) |
| `.assets-revision` is a merged SHA that contains these bundles | FAIL |

Hugging Face discussion #144 (https://huggingface.co/datasets/ChilleD/WebHarbor/discussions/144) is still **open**. `GET /api/datasets/ChilleD/WebHarbor/tree/refs/pr/144` returns 404. `huggingface_hub` `list_repo_files(..., revision="refs/pr/144")` resolves commit `46cb97f965957baf49054cfa976ce1ff5d227b6f` and the five archives `apartments_com.tar.gz`, `eventbrite.tar.gz`, `fandom.tar.gz`, `mayo_clinic.tar.gz`, `smartasset.tar.gz`. `scripts/fetch_assets.sh` refuses any revision other than the pin, so the archives were downloaded with `hf_hub_download` and extracted into the site trees (gitignored). `.assets-revision` was not changed. An open-discussion commit is not a merged asset revision.

Seed md5 of those archives, unchanged across boot and both resets:

| Site | md5 |
| --- | --- |
| apartments_com | `c8b5289e538f12a93cb647798f2841ff` |
| eventbrite | `b84f05830476e2da75cfd49135330523` |
| fandom | `58843e9316018a166ae523e9c8fd6bce` |
| mayo_clinic | `31bc2f4e4ea4627f012b4cb565ef1b75` |
| smartasset | `702c8df74bcaf4d4379489e1f6bf4b4f` |

A local `seed_data` generation does not reproduce those files. Compared with the archives: Apartments.com image-path columns differ (building heroes, galleries, floor plans, articles); Eventbrite differs on `users.password_hash`, `users.created_at`, all 215 `organizers.created_at`, 180 `organizers.follower_seed`, 25 help-article sections, and every event image path; Mayo Clinic differs on 4 `user.password_hash` values (and empty-table column order); SmartAsset differs on all 188 article hero paths. Fandom rows matched an earlier local generation while the SQLite file bytes did not. Runtime `/reset` of the shipped archive is fine because each seed function returns before any commit when the catalog is populated. Do not add a Dockerfile `seed_data.py` step for these four until bcrypt and `datetime.utcnow` defaults are pinned, and do not treat a local rebuild as a substitute for the archive.

### Port 40099

Relative to main `1c1dc23f`, appending after `ryanair` is the correct slot: physical ports `40099`–`40103`, `EXPOSE 8101 40000-40103`. `websyn_start.sh`, `control_server.py`, and the README table agree. This review does not renumber this PR and does not renumber anyone else's.

The same physical index is also claimed by other open heads that append one new site at index 99, even when their `EXPOSE` line advertises a later logical port:

| PR | Last site in `SITES` | Physical last port | `EXPOSE` line |
| --- | --- | --- | --- |
| #242 Porsche review | `porsche` | 40099 | `40000-40099` |
| #241 StubHub | `stubhub` | 40099 | `40000-40099` |
| #240 SourceForge | `sourceforge` | 40099 | `40000-40137` |
| #243 SpotHero | `spothero` | 40099 | `40000-40140` |
| #244 Student.com | `student_com` | 40099 | `40000-40141` |
| #245 Statista | `statista` | 40099 | `40000-40142` |

Older heads still sit on stale bases (#225 Porsche `EXPOSE 40000-40124`, #231 Qatar Airways physical `40094`, #232 SoundCloud physical `40094`, #236 Speedo physical `40097`). Maintainers re-normalize at merge time. Whoever lands second moves.

### Repo hygiene

No `README.md` or `CLAUDE.md` inside the five site directories. Each has a `NOTICE.md`. Verifier tests live under `sites/<site>/verify/test_verifiers.py`, which `.dockerignore` excludes (`sites/*/verify/test*.py`).

## Visual fidelity

Driven in Playwright Chromium (desktop 1280 and 768) against the scoped container. Screenshots were taken under `/tmp/pr239-review/` (not committed).

### Apartments.com — PASS

- Homepage title “Apartments.com — Apartments for Rent”: orange logo, search hero, city chips, listing cards with prices and star ratings.
- Header links `/`, `/search`, `/cities`, `/renters-guide`, `/roommates`, `/renters-insurance`, `/moving-services`, `/list-your-property`, `/login`, `/register` all returned 200.
- Homepage `<img>` count 26, broken 0. Sample heroes decoded at 900×600. Detail page for The Boulevard Austin showed distinct JPEGs (`aus-aspect-2.jpg` 650×433, `aus-frank-1.jpg` 1024×683).
- 768px homepage: no page-level horizontal overflow.
- Nit: 477 of 715 building heroes are AVIF (`ftypavif`) with a `.jpg` name, and 11 are WEBP with a `.jpg` name. Chromium still decoded the ones on the homepage. A client that trusts `Content-Type: image/jpeg` can fail them. Pillow could not open the AVIF files.

### Eventbrite — FAIL

- Desktop home is recognizable: orange wordmark, location menu, “Popular in New York”, category row, newsletter.
- Cards are CSS backgrounds, not `<img>`. Playwright counted 53 `.eb-card-img` nodes, all with a real `url(...)`. A cropped card for “The Great Gatsby Jazz Night” shows a photograph, a Music badge, and “From $27.00”. `GET /static/images/evt_music_011.jpg` returned `image/jpeg`, 83968 bytes.
- **768px homepage overflows horizontally** (`scrollWidth` greater than the viewport). The location list and header wrap into a broken multi-column strip. That fails the responsive check.

### Fandom — PASS

- Homepage is a dark hub with the FANDOM wordmark, wiki links (Marvel Cinematic Universe, Wookieepedia, Genshin Impact), and hero backgrounds pointing at `mcu_avengers…`, `starwars_…`, and `genshin_file…` JPEGs.
- Tony Stark article renders an infobox (birth date, species, affiliation) and a character still. Search for “Tony Stark” returned “15 results” and did not print the birthday on the results page.
- 768px homepage: no page-level overflow.
- Article pages are a simplified wiki, not a pixel copy of fandom.com. Sampled character JPEGs decode as photographs (hundreds to thousands of colors). Fair-use character images are disclosed in `NOTICE.md` and still need a license decision before the archive is merged.

### Mayo Clinic — PASS

- Homepage: blue header, “Request appointment”, “Patient Care” menu, search, condition cards. 11 images, 0 broken. Sample anatomy/wellness photos are real Wikimedia-style images, not flat placeholders (sample color counts 256–2942).
- Mediterranean diet article shows category “Nutrition”, date “May 27, 2026”, and a 960×720 photo. The word “author” is absent.
- Header targets exercised (`/`, `/appointments`) returned 200. 768px: no page-level overflow.
- Provenance is incomplete (illustrative Commons files, synthetic `SIM-MAYO-*` trials). Disclosure is in `NOTICE.md`.

### SmartAsset — PASS

- Homepage: star logo, SmartReads / Tools / Find Advisor nav, article cards. The four visible heroes are SVG illustrations in `articles_v2/` (600×360), which matches the archive paths. Sampled advisor and article JPEGs elsewhere in the tree are photographs.
- Credit-card calculator result panel shows “Paid off in 2y 11m, total interest $1,810”, months 35, and final payment `$10.05`.
- Nav links through `/glossary`, `/login`, and `/advisor-match` returned 200. 768px: no page-level overflow.
- Article photos in the archive have no per-file Pexels license record (`NOTICE.md`).

## Functional depth

Playwright filled the password form (not the header search) and clicked that form’s submit button.

| Site | Login | Register | Stateful write | Notes |
| --- | --- | --- | --- | --- |
| Apartments.com | PASS → `/account`, “Alice” | PASS → `/account` for `review239.apt@example.com` | PASS favorite “The Boulevard”; `/favorites` lists it. Account name edit submitted. | Empty register submit is blocked by HTML5 `required`. |
| Eventbrite | PASS → `/`, header shows Alice, Tickets, Likes, Following. `/account` “Hi Alic…” | PASS signup `review239.eb2@example.com`, then login of that account returns `/` | PASS “Save event” on Science + Fiction becomes “♥ Saved”; `/saved` lists it | 768 overflow is visual, not a dead control. |
| Fandom | PASS → `/`, “Welcome back, AliceJ!” | PASS `ReviewEditor240` shown in the header | PASS Watch on Thanos becomes Unwatch and flashes “Now watching.” | |
| Mayo Clinic | PASS → `/patient-portal`, “Alice Johnson” | PASS → portal as “Review Patient” | Appointment request is a stepped form (`step`, `dept`, `location`, `email`). Empty submit is blocked. A full booking was not completed in this Chromium pass. | No CSRF on state-changing POSTs. |
| SmartAsset | PASS → `/account`, “Welcome back, Alice Johnson.” | PASS “Account created. Welcome to SmartAsset.” | PASS saved “Changed payoff plan” (`credit-card`) appears on `/account/saved` | Calculator GET `balance=5000&apr=22.5&monthly_payment=200` shows `$1,810` and `10.05`. |

Search spot checks: Apartments “The Boulevard Austin” (page contains “Walk 36”); Eventbrite “Austin music” finds Knox & Cell & Friends and the detail page contains `$95`; Fandom “Tony Stark” returns 15 results; Mayo “diabetes” says “Showing 20 results”; SmartAsset “standard deduction” lists the Jeff White article and a Hunter Kuffel near-miss.

## Task quality

PASS means the fixture can answer the question through the UI and the question is not a famous-knowledge shortcut or a listing-card leak. FAIL means send the row back. Graders exist for every row either way; a navigation gate does not repair a shortcut or a leak.

Chromium this session confirmed the listing leaks (Walk 36 and a 4.8 rating are on Apartments search results), the student-housing heading “42 Student Housing properties” with no “42+”, Eventbrite West counts (32 three times, 31 three times, 30 once, 27 once), Fandom recent-changes text “200 revisions shown (page limit 200)”, the Tony Stark page containing the birthday while search results do not, the Mediterranean article with Nutrition and no byline, and the SmartAsset credit-card chips. The other rows were checked against the Hugging Face seed and the routes in the earlier pass on this branch; they were not each clicked again in Chromium.

### Apartments.com — section FAIL (4 of 16 leak)

| Task | Result | Evidence |
| --- | --- | --- |
| --0 | PASS | Miami EV filter total is on that results page and is unique to the filter. |
| --1 | PASS | One cheapest Brickell 2BR at or below $3,500. Rent is bound to that building. |
| --2 | FAIL | Card leak. Search results contain “Walk 36” for The Boulevard Austin. Available-unit count is on the card. |
| --3 | FAIL | Card leak. Both Walk Scores and both rent ranges are on the cards. |
| --4 | PASS | One cheapest available SF 1BR with dogs and in-unit laundry. |
| --5 | PASS | SoMa preset returns one building. Grader uses the matching-unit range shown. |
| --6 | PASS | Stateful tour row plus the stored confirmation number. |
| --7 | FAIL | Card leak. Search for The Wynwood at Chicago includes “4.8” on the results page. Highest-rated card is first. |
| --8 | PASS | Nearest grocery is closer than the other grocery and is not a park. |
| --9 | FAIL | Card leak. Cheapest LA luxury rooftop+pool result is identifiable from the sorted cards, including the rent range. |
| --10 | PASS | One nearby school rated 8 or higher. |
| --11 | PASS | Stateful review on The Symphony (not The Symphony Lofts) and the updated count. |
| --12 | PASS | Alice already has one saved search; the account total includes the new one. |
| --13 | PASS | One cheapest Seattle unit available on or before 2026-06-30 with parking. |
| --14 | PASS | First displayed available unit; building deposit, not the unit deposit. |
| --15 | PASS | Chromium: “See all 42 matching rentals” and “42 Student Housing properties”, no “42+”. New York and San Antonio tie at 5. |

### Eventbrite — PASS

| Task | Result | Evidence |
| --- | --- | --- |
| --0 | PASS | One free NYC music event in the benchmark weekend (`BENCHMARK_NOW` 2026-05-27). |
| --1 | PASS | Stateful GA qty 2. Order code is random and must be read back. |
| --2 | PASS | Free tier makes AI Product Summit cheaper. Prices are bound after the event name so “$0 and AI Product Summit” does not attach 0 to the wrong event. |
| --3 | PASS | Two June online business conferences. E-commerce’s first speaker is the distractor. |
| --4 | PASS | Chromium search “Austin music” shows Knox & Cell & Friends; detail contains $95, Continental Club. |
| --5 | PASS | One NY arts event with the flexible refund label and a stable start date. |
| --6 | PASS | Both tiers sold out. Prompt says “tier” singular; grader requires both names. Wording nit, still answerable. |
| --7 | PASS | Three tiers; expensive tier and timezone are on the event page. |
| --8 | PASS | Stable `DTSTART` and location. `DTSTAMP` uses `utcnow` and is not graded. |
| --9 | PASS | Refund help search returns four articles. |
| --10 | PASS | Music pills Rock, EDM, Hip Hop are an ordered triple. |
| --11 | PASS | Author and published date are on the post. |
| --12 | PASS | Chromium save persists; `/saved` lists the event. |
| --13 | PASS | Stateful free order with the dietary note and a stored code. |
| --14 | PASS | Promo discount is stored on the order. Grader checks that order, not one hardcoded total. |
| --15 | PASS | Alice’s city changes from the seed value. |
| --16 | PASS | Chromium signup then login of the new account. Grader checks identity, not the password. |
| --17 | PASS | Chromium `/region/west`: Los Angeles 31, San Francisco 32, Seattle 27, Denver 32, Portland 31, Phoenix 31, Las Vegas 32, San Diego 30. Three-way tie at 32. |

### Fandom — section FAIL (3 shortcuts)

| Task | Result | Evidence |
| --- | --- | --- |
| --0 | FAIL | Knowledge shortcut. Chromium article shows “May 29, 1970”. Search results do not, but the date is famous without the site. |
| --1 | PASS | Species string “Titan (Eternal-Deviant hybrid)” is fixture-specific. |
| --2 | PASS | Zhongli constellation “Lapidus” differs from the usual canon name. Version is bound to Zhongli. |
| --3 | FAIL | Knowledge shortcut. Purple blade and Vaapad are famous. |
| --4 | PASS | Category lists exactly four people. Extra Guardians fail the grader. |
| --5 | PASS | Arlecchino element, weapon, region, and constellation. Childe is the near-miss. |
| --6 | PASS | Chromium heading: “200 revisions shown (page limit 200)”. Non-bot table has 245; the displayed answer is 200. |
| --7 | PASS | History length is printed on the page. |
| --8 | PASS | Weak: newest and previous Hu Tao deltas are both +60, so the sign is not a unique newest-edit signal. Still page-specific. |
| --9 | FAIL | Knowledge shortcut. Tatooine’s three moons are famous. Chromium article mentions moons. |
| --10 | PASS | Stateful new user with no edits. Avatar color is random and is not graded. |
| --11 | PASS | Chromium Watch on Thanos (not pre-seeded) becomes Unwatch. |
| --12 | PASS | Revision summary and the new sentence must both be stored. |
| --13 | PASS | Liyue total moves 71 → 72. Users may vote more than once; grader reads the stored total. |
| --14 | PASS | What-links-here is a fixed article set. |
| --15 | PASS | Reply count is bound to the named pinned thread. The other pinned thread has a different count. Opening it no longer writes `view_count`. |
| --16 | PASS | One active poll question per wiki. |
| --17 | PASS | Cathedral uploader is distinct from the concept-painting uploader. `test_asset_manifest_and_references` passes once `mcu_avengers__endgame.jpg` is extracted from the archive. |

### Mayo Clinic — section FAIL (shortcut + missing byline)

| Task | Result | Evidence |
| --- | --- | --- |
| --0 | FAIL | Knowledge shortcut. Diabetes prevention text is generic lifestyle boilerplate shared across the diabetes pages. |
| --1 | PASS | Four named drugs. A related condition’s drug is a distractor. |
| --2 | PASS | Adult acute chest pain surfaces pulmonary embolism as urgent. |
| --3 | PASS | Chronic adult fatigue lists several routine causes; grader requires a majority. |
| --4 | PASS | Both procedures are Orthopedics. Lookalikes in other departments fail. |
| --5 | PASS | One Jacksonville cardiologist who lists Spanish. |
| --6 | PASS | One synthetic trial id and intervention. |
| --7 | PASS | Indication, side effects, and warning are on the drug page. |
| --8 | PASS | CABG is tied to coronary artery disease and to the department display name. |
| --9 | PASS | Stateful. Code is computable from email and date, so the grader requires the appointment row. Chromium opened the stepped request form; a full submit was not finished in this pass. |
| --10 | FAIL | Not answerable as an author. Chromium article: “Nutrition · May 27, 2026” and no byline. `Article` has no author column. The verifier accepts only an explicit no-byline answer plus Nutrition. |
| --11 | PASS | Count is the full Jacksonville neurology list. The location filter adds nothing. |
| --12 | PASS | Loose: doctors are the neurology department, not an MS-only panel. |
| --13 | PASS | Phase 2 + Recruiting + Rochester is a stable count. |
| --14 | PASS | One of the four named drugs is absent. Calling a present drug missing fails. |
| --15 | PASS | Imaging category and letter M produce a fixed set. |
| --16 | PASS | One trial is linked through that department’s doctors. |
| --17 | PASS | Interaction warning is on the page. The long description is generic. |
| --18 | PASS | Woodworking detail is synthetic and page-specific. |
| --19 | PASS | Portal shows the seed confirmation code and the saved-item count. Login to the portal was confirmed in Chromium. |

### SmartAsset — PASS

| Task | Result | Evidence |
| --- | --- | --- |
| --0 | PASS | Chromium result: months 35, interest `$1,810`, final payment `$10.05`. |
| --1 | PASS | Each payment is bound to its own months and interest. “19.9%” does not count as 19 months. Swapping the scenarios fails. |
| --2 | PASS | Month savings are exact. Interest savings accept the rounded chip and the precise difference. |
| --3 | PASS | Final balance, deposits, and interest are separate chips. |
| --4 | PASS | Deduction used is not a chip. It is the standard deduction, which beats the itemized input. Tax year 2025 is on the page. |
| --5 | PASS | Each state is bound to its own estimate, plus the limitation notice. |
| --6 | PASS | Per-paycheck net and annual take-home for the stated filing, state, and pre-tax inputs. |
| --7 | PASS | Both directions are bound to the destination city. Raw indexes are not rendered; percent and direction are. |
| --8 | PASS | Principal-and-interest is distinct from the total monthly payment. |
| --9 | PASS | Nest egg and “not on track” under untouched life-expectancy and Social Security defaults. Shortfall dollars depend on the default and are not required. |
| --10 | PASS | One California tax advisor at the $250,000 minimum cap. |
| --11 | PASS | One Florida tax advisor. An empty-result answer fails. |
| --12 | PASS | Thin. Chromium search and article show Jeff White, CEPF, 5 min, and the standard-versus-itemize dek. Body text is generic. |
| --13 | PASS | Thin. Same author as --12. The tax-timing line is the dek. Author alone fails. |
| --14 | PASS | Chromium register plus a saved credit-card row labeled “Changed payoff plan” on `/account/saved`. |
| --15 | PASS | Alice’s saved savings row and its summary. |
| --16 | PASS | Row must be observed and then absent. Logout must be followed by the sign-in page. |
| --17 | PASS | Other assets stay at the form default of $5,000. The zeroed-default net worth fails. |

## Grading contract

90 deterministic verifiers: `sites/<site>/verify/verify_N.py`, shared `verify_lib.py`, `checks.py`, and `contracts.py`. Ground truth stays in `contracts.py`. Rubrics are fact checkpoints, not answers.

```bash
python3 -m unittest discover -s sites/<site>/verify -p 'test_*.py'
```

`eval_judge.py --verifier True` runs `verify_N.py --run_dir <dir>`. Stateful tasks read `initial_state.db` and `after_state.db` in the run directory when those paths are not passed. Each package’s tests cover an empty answer, a correct answer with no navigation, a wrong answer on the right URLs, a correct self-report with an unchanged database, and a passing trajectory.

## Required before merge

1. Merge Hugging Face discussion #144 (or a reviewed replacement), set `.assets-revision` to that merged commit, and fetch clean. Do not pin `46cb97f`.
2. At merge time, re-slot these five indexes if another append-at-99 PR has already landed. Update `SITES`, the control-plane list, `EXPOSE`, and the README table together. Do not renumber the other open PRs from this branch.
3. Send back or re-anchor: Fandom--0, Fandom--3, Fandom--9, Mayo Clinic--0, Mayo Clinic--10, and Apartments.com--2, --3, --7, --9 (strip Walk Score, rating, review count, and rent range off listing cards, or rewrite the questions so the card is not the answer).
4. Fix Eventbrite at 768px so the homepage does not scroll horizontally.
5. Keep the shipped archives. Do not rebuild them in Docker from `seed_data.py` until the nondeterministic bcrypt and `utcnow` writes are pinned.

## What this review branch changes

- Verifiers, rubrics, and the seven-key task rows for all 90 tasks. Site task-schema tests expect `verifier_path` and `judge_rubric` and still reject an `answer` key.
- Fandom article and forum GETs no longer commit `view_count`.
- Fandom recent-changes heading states the 200-row page limit.
- Apartments.com `/student-housing` renders all 42 buildings and hides the “+”.
- Eventbrite `/region/<slug>` prints each city’s full upcoming count.

## Security nits

No user-controlled SQL string building in the request handlers. Open redirects on Apartments, Eventbrite, and Mayo reject off-site `next` values. Secrets are hardcoded development keys. Eventbrite and Mayo have no CSRF on state-changing POSTs. Apartments, Fandom, and SmartAsset use `CSRFProtect`. Acceptable for an offline benchmark.

## What was run this pass

- Docker 29.1.3 installed (`apt-get install docker.io`); `systemd` would not start the daemon, so `containerd` and `dockerd --host=unix:///var/run/docker.sock` were started by hand.
- Scoped image build and the control-plane checks in the mechanical table, including a post-mutation `/reset-all`.
- Hugging Face #144 download via `refs/pr/144` @ `46cb97f`, extract, image-path existence check (Apartments heroes 715/715, Eventbrite event images 933/933 and 20/20 blog covers, SmartAsset article heroes 188/188).
- Playwright Chromium: homepages, 768px, nav, login, register, search, favorite / save / watch / saved calculation, and the task pages named above.
- Fandom `test_asset_manifest_and_references`: OK after the archive extract.
- `git rebase 1c1dc23f5fabdaaef67c6d3bbf87bcd6915b9518`: already up to date.

Not run: the official 104-site `./scripts/build.sh`, a 104-site HTTP sweep, and LLM-agent trajectories (`agent_demo`). Verifier unit tests were run in the previous pass on this branch and were not repeated after the asset extract, because the extract does not change verifier code.
