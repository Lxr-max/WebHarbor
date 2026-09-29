# Review: PR #239 — five reserved mirrors

Review of [#239](https://github.com/aiming-lab/WebHarbor/pull/239), hqhq1025's five mirrors and 90 tasks at contributor commit `7920869974bd82573713d9faefefb733546233d5`. [#251](https://github.com/aiming-lab/WebHarbor/pull/251), `Lxr-max/WebHarbor:review/pr239`, preserves that commit and adds the reviewer continuation. This report combines the earlier Chromium, scoped-Docker, and Hugging Face evidence with the 2026-09-30 Linux checks and the post-edit verifier tests recorded below. Docker and Chromium were not re-run on 2026-09-30.

**Verdict: do not merge #239 yet. Functional depth passes; upstream ports, merged assets, nine returned tasks, and Eventbrite's 768px layout remain blockers. #251 does not re-slot ports or change `.assets-revision`.**

## Mechanical checks: FAIL

Local checks pass on this branch's `1c1dc23f` base; the asset pin and upstream port conflicts do not.

- [x] 2026-09-30 Linux pass, Python 3.12, with the `refs/pr/144` archives extracted: `py_compile` of all five `app.py` files passed.
- [x] That pass: `python scripts/check_site_registry.py` reported **104 sites consistent**, `EXPOSE (8101 40000-40103)`. This establishes branch-local consistency, not compatibility with current upstream main.
- [x] That pass: `pytest sites/<site>/verify` and `pytest sites/<site>/tests` passed as listed below.
- [x] Post-edit Windows pass, Python 3.12.13, `PYTHONUTF8=1`: `python -m pytest -q -p no:cacheprovider sites/<site>/verify` passed separately for all five sites, including the new schema/no-leak test.
- [ ] Full-image build and all-site HTTP sweep. The official `./scripts/build.sh` was not run in the earlier pass: only these five seeds were present, and the branch pin `5d2b17fa21067990370f8e7fc27123a1c24d7802` did not contain their bundles. No full-image result is claimed here.
- [ ] Adopt upstream-compatible ports and a merged asset revision containing all five archives.

| Site | Linux verifier tests / subtests (before edits) | Linux site tests | Windows verifier tests / subtests (after edits) |
| --- | --- | --- | --- |
| apartments_com | 2 / 67 passed | 13 passed | 3 / 83 passed |
| eventbrite | 2 / 78 passed | 16 passed | 3 / 96 passed |
| fandom | 2 / 76 passed | 13 passed | 3 / 94 passed |
| mayo_clinic | 2 / 81 passed | 11 passed | 3 / 101 passed |
| smartasset | 5 / 75 passed | 21 passed | 6 / 93 passed |

### Registry against upstream main

As of 2026-09-30, upstream main is `90c91a69`: **112 registered sites**, ending with `trip_com` on **40111**. SourceForge is on 40104 and Statista on 40108. This branch still appends its five sites after `ryanair` on base `1c1dc23f` (99 sites, last port 40098).

| Site | Slug | Branch index / port | Current upstream occupant | Required index / port |
| --- | --- | --- | --- | --- |
| Apartments.com | `apartments_com` | 99 / 40099 | Chess.com | 112 / 40112 |
| Eventbrite | `eventbrite` | 100 / 40100 | Porsche | 113 / 40113 |
| Fandom | `fandom` | 101 / 40101 | Qatar Airways | 114 / 40114 |
| Mayo Clinic | `mayo_clinic` | 102 / 40102 | SoundCloud | 115 / 40115 |
| SmartAsset | `smartasset` | 103 / 40103 | Speedo | 116 / 40116 |

The offered contributor follow-up branch `Lxr-max/WebHarbor:fix/pr239-returned-tasks` merges main, re-slots these sites to 40112–40116, re-anchors the nine returned tasks, and fixes Eventbrite's 768px overflow. It is **not part of #251**. Once #239 adopts it, this review branch will be refreshed for the ports and the nine tasks' verifiers/rubrics.

### Earlier scoped-Docker evidence

The earlier pass built `webharbor:pr239-five` from `python:3.12-slim-bookworm` and `requirements.lock` using `pip install --require-hashes`. It copied the real `site_runner.py`, `control_server.py`, and these five trees with HF seeds/images. `SITES` was reduced to the five names, `BASE_PORT=40099`; host mappings were `8201:8101` and `41099–41103:40099–40103`. The scoped Dockerfile was not committed. Docker 29.1.3 was installed through `docker.io`; `containerd` and `dockerd --host=unix:///var/run/docker.sock` were started manually after systemd did not start the daemon.

| Check in the earlier pass | Result |
| --- | --- |
| Five homepages HTTP 200 (`41099`–`41103`) | PASS |
| `GET /health` with bearer token, all five `alive` and `ready` | PASS |
| Boot md5(instance) == md5(instance_seed) for all five | PASS |
| `POST /reset/<site>` then md5 match | PASS (each ~0.8s) |
| `POST /reset-all` then md5 match | PASS (1.10s) |
| Same `/reset-all` after Playwright logins, registers, favorites, watches, and saved calculations left all five instance DBs dirty | PASS (1.17s); homepages 200 again |
| Full 104-site HTTP sweep | not run (other seeds absent) |
| `.assets-revision` is a merged SHA that contains these bundles | FAIL |

### Hugging Face assets

[ChilleD/WebHarbor discussion #144](https://huggingface.co/datasets/ChilleD/WebHarbor/discussions/144) remains **open**, checked 2026-09-30. `refs/pr/144` resolves to `46cb97f965957baf49054cfa976ce1ff5d227b6f`. Upstream main's `.assets-revision` pins `f63db8a547bbbed35eb457b4109d43d5392f3756`, which does not contain these archives. An accessible open-PR commit is not a merged asset revision.

In the earlier pass, `GET /api/datasets/ChilleD/WebHarbor/tree/refs/pr/144` returned 404, while `huggingface_hub.list_repo_files(..., revision="refs/pr/144")` resolved the commit and five archives. Since `scripts/fetch_assets.sh` refused a revision other than the pin, the bundles were downloaded with `hf_hub_download` and extracted into the gitignored site trees. The asset pin was left unchanged. Image-path checks found Apartments heroes 715/715, Eventbrite event images 933/933 and blog covers 20/20, and SmartAsset article heroes 188/188.

| Archive | SHA-256 | Seed md5, unchanged across earlier boot/resets |
| --- | --- | --- |
| apartments_com.tar.gz | `1c3a906b1ca43ce40c25817f199cad26279ceef8e0b8f4e586e613c621ed47f5` | `c8b5289e538f12a93cb647798f2841ff` |
| eventbrite.tar.gz | `5f8122cd49755ee5e4d15798d5e7b69991ce0f288051ac603f7606efa090642e` | `b84f05830476e2da75cfd49135330523` |
| fandom.tar.gz | `01cf45d12b984f6887c56a4d6109f2b3feb3b542a0b146cf94ff21e4819cc46a` | `58843e9316018a166ae523e9c8fd6bce` |
| mayo_clinic.tar.gz | `84a439d1f2b1ebf9973f9e58a2cabf31fa45f66f337e7a4d5797016ceae6d684` | `31bc2f4e4ea4627f012b4cb565ef1b75` |
| smartasset.tar.gz | `3a139bc4d7a2726dae8eb011f611cf2e282a3c44fba654364c5568b6dcb24edd` | `702c8df74bcaf4d4379489e1f6bf4b4f` |

In the earlier pass, local `seed_data` generation does not reproduce those files. Compared with the archives: Apartments.com image-path columns differ (building heroes, galleries, floor plans, articles); Eventbrite differs on `users.password_hash`, `users.created_at`, all 215 `organizers.created_at`, 180 `organizers.follower_seed`, 25 help-article sections, and every event image path; Mayo Clinic differs on 4 `user.password_hash` values (and empty-table column order); SmartAsset differs on all 188 article hero paths. Fandom rows matched an earlier local generation while the SQLite file bytes did not. Runtime `/reset` of the shipped archive is fine because each seed function returns before any commit when the catalog is populated. Do not add a Dockerfile `seed_data.py` step for these four until bcrypt and `datetime.utcnow` defaults are pinned, and do not treat a local rebuild as a substitute for the archive.

- [x] Repo hygiene: each site has `NOTICE.md`; the only README added under each site is `verify/README.md`. No per-site review reports. Verifier tests remain at `sites/<site>/verify/test_verifiers.py`, excluded by `.dockerignore` (`sites/*/verify/test*.py`).

## Visual fidelity: FAIL

Earlier pass: Playwright Chromium at desktop 1280 and 768 against the scoped container. Screenshots were saved locally under `/tmp/pr239-review/`; they were not published or committed. Chromium was not re-run on 2026-09-30.

### Apartments.com — PASS

- [x] Homepage title “Apartments.com — Apartments for Rent”: orange logo, search hero, city chips, listing cards with prices and star ratings.
- [x] Header links `/`, `/search`, `/cities`, `/renters-guide`, `/roommates`, `/renters-insurance`, `/moving-services`, `/list-your-property`, `/login`, `/register` all returned 200.
- [x] Homepage `<img>` count 26, broken 0. Sample heroes decoded at 900×600. Detail page for The Boulevard Austin showed distinct JPEGs (`aus-aspect-2.jpg` 650×433, `aus-frank-1.jpg` 1024×683).
- [x] 768px homepage: no page-level horizontal overflow.
- [ ] Nit: 477 of 715 building heroes are AVIF (`ftypavif`) with a `.jpg` name, and 11 are WEBP with a `.jpg` name. Chromium still decoded the ones on the homepage. A client that trusts `Content-Type: image/jpeg` can fail them. Pillow could not open the AVIF files.

### Eventbrite — FAIL

- [x] Desktop home is recognizable: orange wordmark, location menu, “Popular in New York”, category row, newsletter.
- [x] Cards are CSS backgrounds, not `<img>`. Playwright counted 53 `.eb-card-img` nodes, all with a real `url(...)`. A cropped card for “The Great Gatsby Jazz Night” shows a photograph, a Music badge, and “From $27.00”. `GET /static/images/evt_music_011.jpg` returned `image/jpeg`, 83968 bytes.
- [ ] **768px homepage overflows horizontally** (`scrollWidth` greater than the viewport). The location list and header wrap into a broken multi-column strip. That fails the responsive check.

### Fandom — PASS

- [x] Homepage is a dark hub with the FANDOM wordmark, wiki links (Marvel Cinematic Universe, Wookieepedia, Genshin Impact), and hero backgrounds pointing at `mcu_avengers…`, `starwars_…`, and `genshin_file…` JPEGs.
- [x] Tony Stark article renders an infobox (birth date, species, affiliation) and a character still. Search for “Tony Stark” returned “15 results” and did not print the birthday on the results page.
- [x] 768px homepage: no page-level overflow.
- [ ] Article pages are a simplified wiki, not a pixel copy of fandom.com. Sampled character JPEGs decode as photographs (hundreds to thousands of colors). Fair-use character images are disclosed in `NOTICE.md` and still need a license decision before the archive is merged.

### Mayo Clinic — PASS

- [x] Homepage: blue header, “Request appointment”, “Patient Care” menu, search, condition cards. 11 images, 0 broken. Sample anatomy/wellness photos are real Wikimedia-style images, not flat placeholders (sample color counts 256–2942).
- [x] Mediterranean diet article shows category “Nutrition”, date “May 27, 2026”, and a 960×720 photo. The word “author” is absent.
- [x] Header targets exercised (`/`, `/appointments`) returned 200. 768px: no page-level overflow.
- [ ] Provenance is incomplete (illustrative Commons files, synthetic `SIM-MAYO-*` trials). Disclosure is in `NOTICE.md`.

### SmartAsset — PASS

- [x] Homepage: star logo, SmartReads / Tools / Find Advisor nav, article cards. The four visible heroes are SVG illustrations in `articles_v2/` (600×360), which matches the archive paths. Sampled advisor and article JPEGs elsewhere in the tree are photographs.
- [x] Credit-card calculator result panel shows “Paid off in 2y 11m, total interest $1,810”, months 35, and final payment `$10.05`.
- [x] Nav links through `/glossary`, `/login`, and `/advisor-match` returned 200. 768px: no page-level overflow.
- [ ] Article photos in the archive have no per-file Pexels license record (`NOTICE.md`).

## Functional depth: PASS

Earlier pass: Playwright filled the password form (not the header search) and clicked that form’s submit button.

| Site | Login | Register | Stateful write | Notes |
| --- | --- | --- | --- | --- |
| Apartments.com | PASS → `/account`, “Alice” | PASS → `/account` for `review239.apt@example.com` | PASS favorite “The Boulevard”; `/favorites` lists it. Account name edit submitted. | Empty register submit is blocked by HTML5 `required`. |
| Eventbrite | PASS → `/`, header shows Alice, Tickets, Likes, Following. `/account` “Hi Alic…” | PASS signup `review239.eb2@example.com`, then login of that account returns `/` | PASS “Save event” on Science + Fiction becomes “♥ Saved”; `/saved` lists it | 768 overflow is visual, not a dead control. |
| Fandom | PASS → `/`, “Welcome back, AliceJ!” | PASS `ReviewEditor240` shown in the header | PASS Watch on Thanos becomes Unwatch and flashes “Now watching.” | |
| Mayo Clinic | PASS → `/patient-portal`, “Alice Johnson” | PASS → portal as “Review Patient” | Appointment request is a stepped form (`step`, `dept`, `location`, `email`). Empty submit is blocked. A full booking was not completed in that earlier Chromium pass. | No CSRF on state-changing POSTs. |
| SmartAsset | PASS → `/account`, “Welcome back, Alice Johnson.” | PASS “Account created. Welcome to SmartAsset.” | PASS saved “Changed payoff plan” (`credit-card`) appears on `/account/saved` | Calculator GET `balance=5000&apr=22.5&monthly_payment=200` shows `$1,810` and `10.05`. |

Search spot checks: Apartments “The Boulevard Austin” (page contains “Walk 36”); Eventbrite “Austin music” finds Knox & Cell & Friends and the detail page contains `$95`; Fandom “Tony Stark” returns 15 results; Mayo “diabetes” says “Showing 20 results”; SmartAsset “standard deduction” lists the Jeff White article and a Hunter Kuffel near-miss.


- [x] Auth, registration, search, and the stateful actions in the table were exercised in the earlier pass.
- [ ] Recorded limits: no full Mayo appointment booking in Chromium; Eventbrite and Mayo lack CSRF on state-changing POSTs. The earlier code review found no user-controlled SQL string building; Apartments, Eventbrite, and Mayo rejected off-site `next` redirects. Development secrets are hardcoded. Apartments, Fandom, and SmartAsset use `CSRFProtect`. These security limits were accepted for the offline benchmark, not as production guarantees.

## Task quality: FAIL

PASS means the fixture can answer the question through the UI and the question is not a famous-knowledge shortcut or a listing-card leak. FAIL means send the row back. Graders exist for every row either way; a navigation gate does not repair a shortcut or a leak.

The earlier Chromium pass confirmed the listing leaks (Walk 36 and a 4.8 rating are on Apartments search results), the student-housing heading “42 Student Housing properties” with no “42+”, Eventbrite West counts (32 three times, 31 three times, 30 once, 27 once), Fandom recent-changes text “200 revisions shown (page limit 200)”, the Tony Stark page containing the birthday while search results do not, the Mediterranean article with Nutrition and no byline, and the SmartAsset credit-card chips. The other rows were checked against the Hugging Face seed and the routes in the earlier pass on this branch; they were not each clicked again in Chromium.

- [x] **81 tasks PASS** on the reviewed fixture.
- [ ] **Nine tasks FAIL** and remain returned to the contributor; the offered follow-up is not incorporated here. No task question was changed in this pass.

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
| --9 | PASS | Stateful. Code is computable from email and date, so the grader requires the appointment row. Chromium opened the stepped request form; a full submit was not finished in that earlier pass. |
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

- [x] All 90 rows have exactly `web_name`, `id`, `ques`, `web`, `upstream_url`, `verifier_path`, and `judge_rubric`. Each indexed path exists; there is no answer key.
- [x] `sites/<site>/verify/verify_N.py` calls `verify_lib.main(index)`. Frozen expected values and state callbacks live in `contracts.py`; shared text matchers live in `checks.py`. Each package now has a `verify/README.md` describing its actual run signature and limits.
- [x] Rubrics were checked against expected numbers, names, codes, dates, and outcome predicates. Six were made rules-only, synchronized in `tasks.jsonl` and `contracts.py`: Eventbrite--6 and --13, Fandom--10, Mayo Clinic--5 and --10, SmartAsset--9. Questions and verifier logic are unchanged.
- [x] Each `test_verifiers.py` covers no-op, correct-answer/no-navigation shortcut, wrong-answer, unchanged-state self-report for stateful tasks, and passing fixtures. New tests enforce schema, indexed paths, rubric synchronization, and practical numeric/literal no-leak checks, allowing inputs already stated in the question and guarding the audited outcome leaks. These are synthetic fixtures, not browser trajectories.

```bash
python agent_demo/eval_judge.py --run_dir /absolute/path/to/task-run --verifier True
python -m pytest -q -p no:cacheprovider sites/<site>/verify
```

`eval_judge.py` reads the trajectory's `verifier_path` and invokes it with `--run_dir`. The verifier reads `trajectory.json`, including `final_answer`, step URLs, and `final_url`. For stateful tasks, if neither `--initial_db` nor `--after_db` is supplied and either run-directory snapshot exists, it passes both `initial_state.db` and `after_state.db` paths; a partially supplied explicit pair disables that fallback. It does not fetch container state. Output is JSON `{task_id, pass, reason, evidence[]}`, with exit 0/1 for a completed PASS/FAIL evaluation. Invalid inputs can raise without verdict JSON.

The current harness does not authenticate screenshots, task identity, completion flags, or local URL origin; read-only tasks do not enforce database immutability. State checks are task-specific. A navigation gate does not repair the nine rejected task questions. No end-to-end `agent_demo` trajectories or secondary judge run are claimed.

## Reviewer fixes on this branch

- [x] Preserve contributor commit `79208699`; add 90 verifiers, rules-only rubrics, seven-key task rows, verifier READMEs, schema/no-leak regressions, and this report at `review-reports/pr239-five-mirrors.md`.
- [x] Fandom article and forum GETs no longer commit `view_count`.
- [x] Fandom recent-changes heading states the 200-row page limit.
- [x] Apartments.com `/student-housing` renders all 42 buildings and hides the “+”.
- [x] Eventbrite `/region/<slug>` prints each city's full upcoming count.

No port re-slot or `.assets-revision` change is included. The following rubric edits remove answer-bearing wording without changing task questions or grading logic:

| Task | Old wording | Replacement rule |
| --- | --- | --- |
| Eventbrite--6 | “only one tier when both are sold out” | Reject an incomplete list of sold-out tiers without revealing its size. |
| Eventbrite--13 | “Report the $0.00 total” | Report the persisted receipt total and order code; require a matching stored order. |
| Fandom--10 | “edit count of 0” / “claim of 0 edits” | Report the displayed edit count and require the new account. |
| Mayo Clinic--5 | “Another Jacksonville cardiologist” | “A Jacksonville doctor”; do not supply the requested specialty. |
| Mayo Clinic--10 | “The page does not show an author byline” / “no author is displayed” | Report whether a byline is present and reproduce it if present. |
| SmartAsset--9 | “An on-track claim fails.” | Reject a conclusion that contradicts the displayed result. |

## Required before upstream merge

- [ ] Merge HF discussion #144 (or a reviewed replacement) while preserving unrelated assets, confirm its actual merged status, pin an immutable merged revision containing all five archives, and fetch clean. Do not use open-PR commit `46cb97f` as a merged pin. Resolve the recorded media-license/provenance gaps before publishing the archive.
- [ ] Have #239 adopt the offered `Lxr-max:fix/pr239-returned-tasks` follow-up, or equivalent contributor fixes: merge current main, re-slot the five sites to **40112–40116** in the stated order, and align both registries, `EXPOSE`, task URLs, and only the README Websites table.
- [ ] Re-anchor **Apartments.com--2, --3, --7, --9; Fandom--0, --3, --9; Mayo Clinic--0, --10**. Remove listing-card answers or require page-specific details; replace knowledge shortcuts and the missing-byline question.
- [ ] Fix Eventbrite's 768px homepage overflow and recheck it in Chromium.
- [ ] After contributor adoption, refresh #251's ports and the nine tasks' verifiers/rubrics; repeat task review and the grading suites. Integrate the original contribution before the reviewer continuation, preserving ancestry.
- [ ] Keep the reviewed archives rather than rebuilding them from the non-reproducing seed scripts. Validate the combined code and freshly fetched merged assets with the full-image build, all-site HTTP/health checks, and byte-identical reset checks before upstream merge.
