# Review: PR #239 — five reserved mirrors

Upstream: https://github.com/aiming-lab/WebHarbor/pull/239
Author: hqhq1025
Head: `hqhq1025/WebHarbor` `feat/reserved-five-mirrors-20260927` @ `7920869974bd82573713d9faefefb733546233d5`
This review branch: `review/pr239` on `Lxr-max/WebHarbor`, based on that head.

Sites: Apartments.com (`40099`), Eventbrite (`40100`), Fandom (`40101`), Mayo Clinic (`40102`), SmartAsset (`40103`). 90 tasks. Contributor `tasks.jsonl` rows had only `web_name`, `id`, `ques`, `web`, `upstream_url`. No answer keys were present, and none were added.

HF asset discussion: https://huggingface.co/datasets/ChilleD/WebHarbor/discussions/144 — still **open** as of this review (title “Add asset bundles for five reserved mirrors (GitHub #239)”).

## Verdict

Do not merge #239 yet. The five apps are real Flask mirrors with working auth and stateful flows, and a frozen seed resets byte-identically. Merge is blocked by unpinned assets, a physical port collision with other open site PRs, scratch-rebuild nondeterminism on four sites, and a handful of tasks that are either famous-knowledge shortcuts or not answerable as written.

This branch adds the missing grading contracts (90 deterministic verifiers, subject-bound, DB-checked for stateful tasks) and four small feasibility fixes that do not rewrite the seed archives. It does not re-slot ports and does not point `.assets-revision` at the unmerged HF discussion.

## Blocking

1. **Assets are not pinned.** `.assets-revision` is still `5d2b17fa21067990370f8e7fc27123a1c24d7802` (“HF asset PRs #139 and #140”). `assets-manifest.json` has no `apartments_com`, `eventbrite`, `fandom`, `mayo_clinic`, or `smartasset` archive. The Dockerfile runs `check_seed_databases.py` and has no `seed_data.py` build step for these five sites, so a clean image build fails closed until the archives are in the build context. HF discussion #144 is open, not merged. An open-discussion commit is not a merged asset revision. Do not bump `.assets-revision` until that discussion is actually merged and the combined tree is rebuilt.

2. **Port 40099 is already the next physical slot for several other open PRs.** Inside this PR the registry is consistent: `websyn_start.sh`, `control_server.py`, and the README table all append the five sites after `ryanair`, and the Dockerfile `EXPOSE`s `8101 40000-40103` (104 sites, ports `40099`–`40103`). That is the right shape for “append after current main.” It is not free to merge as-is. On current main (99 sites, last port `40098`) these open heads also occupy physical index 99 / port `40099`, even when their `EXPOSE` line still advertises a later logical wave port:

   | PR | Last site in `SITES` | Physical last port | `EXPOSE` line |
   | --- | --- | --- | --- |
   | #242 Porsche review | `porsche` | 40099 | `40000-40099` |
   | #241 StubHub | `stubhub` | 40099 | `40000-40099` |
   | #240 SourceForge | `sourceforge` | 40099 | `40000-40137` |
   | #243 SpotHero | `spothero` | 40099 | `40000-40140` |
   | #244 Student.com | `student_com` | 40099 | `40000-40141` |
   | #245 Statista | `statista` | 40099 | `40000-40142` |

   Older wave heads still sit on stale bases (#225 Porsche `EXPOSE 40000-40124`, #231 Qatar Airways physical `40094`, #232 SoundCloud physical `40094`, #236 Speedo physical `40097`). Raibows’s standing rule is to re-normalize at merge time. This review does not silently re-slot #239. Whoever merges must assign the five indexes after whatever has actually landed, then keep `SITES`, the control-plane list, `EXPOSE`, and the README table together.

3. **A from-scratch seed rebuild is not a drop-in replacement for the frozen archive, except Apartments.com.** Copying each existing `instance_seed/*.db` into `instance/` and importing the app twice left the file bytes unchanged for all five (see “What was run”). Rebuilding from an empty database with `PYTHONHASHSEED=0` matched Apartments.com byte-for-byte (`dec0bd35142b358069757d67b5682901`) and did not match the other four:

   - Eventbrite: 4 `users.password_hash` values (`bcrypt.generate_password_hash`), 4 `users.created_at` values, and all 215 `organizers.created_at` values (`datetime.utcnow` column default). Other columns matched.
   - Mayo Clinic: 4 `user.password_hash` values. `seed_benchmark_users()` calls `bcrypt.generate_password_hash("TestPass123!")` whenever Alice is absent. Other columns matched.
   - Fandom and SmartAsset: every compared row matched (Fandom passwords are pinned; SmartAsset benchmark hashes are pinned), but the SQLite file bytes still differed.

   Runtime `/reset` of a shipped archive is fine, because each seed function returns before any commit when the catalog is already populated. Regenerating the HF bundles from this code will not reproduce those four archives. Pin the merged archive; do not treat `seed_data.py` as a byte-stable Dockerfile step for those four until the wall-clock defaults and random bcrypt calls are removed.

4. **Five tasks should be sent back or re-anchored.** Navigation gates stop a pure no-op, but they do not satisfy the contributor rule that a task must be unanswerable without the site:

   - Fandom--0 Tony Stark’s birthday (May 29, 1970).
   - Fandom--3 Mace Windu’s purple lightsaber / Vaapad.
   - Fandom--9 Tatooine’s three moons.
   - Mayo Clinic--0 diabetes prevention. The paragraph is generic lifestyle boilerplate shared across the diabetes pages, and it is also ordinary medical advice.
   - Mayo Clinic--10 asks for the author byline of “Mediterranean Diet: A Heart-Healthy Eating Plan.” `Article` has no author column. The template shows category and date only. There is no byline to report. The verifier accepts only an explicit “no author / no byline” answer plus the category Nutrition. As written, the task asks for a fact the fixture does not contain.

## What this review branch changes

- `sites/<site>/verify/verify_N.py` plus `verify_lib.py`, `checks.py`, `contracts.py`, and `test_verifiers.py` for all 90 tasks. Ground truth stays in `contracts.py`. `tasks.jsonl` gains `verifier_path` and `judge_rubric` only. Rubrics state checkpoints, not answers.
- Stateful graders read the after-database read-only and reject a correct self-report when the row is missing. Numbers are bound to the entity (a right rent on the wrong building fails; swapped calculator scenarios fail).
- Fandom article and forum GETs no longer commit `view_count`. A read-only grading run was dirtying the live DB.
- Fandom recent-changes heading now says how many revisions are actually shown and that the page limit is 200. The query is still `limit(200)`. Non-bot Wookieepedia revisions are 245; the displayed answer is 200.
- Apartments.com `/student-housing` no longer stops at 24. All 42 student buildings render, with no “+” on the count, so the New York / San Antonio tie is visible. City, senior, and military lists are unchanged.
- Eventbrite `/region/<slug>` prints each city’s full upcoming-event count, not only the 60-card preview. West is a three-way tie at 32 (San Francisco, Denver, Las Vegas).
- The five sites’ own task-schema tests now expect the reviewer keys and still reject an `answer` key.

## Nits

- Apartments search cards show Walk Score, rating, review count, and rent range, so Apartments--2, --3, --7, and --9 can be finished from the result card without opening the building. Not changed here.
- Eventbrite--6 says “the ticket tier” while both tiers are sold out. The verifier requires both names.
- Eventbrite ICS `DTSTAMP` uses `utcnow()`, so the download is not fully deterministic. `DTSTART` and location are stable and are what the grader checks.
- Eventbrite checkout and Mayo appointment/account POSTs have no CSRF protection. Apartments, Fandom, and SmartAsset use `CSRFProtect`. Acceptable for an offline benchmark, worth fixing before any public deployment.
- Fandom registration picks `avatar_color` with `random.randint`. That does not affect reset of the seed; it does make a newly registered profile’s color unstable.
- Apartments benchmark passwords are `pbkdf2:sha256:1` on purpose so the seed stays deterministic. Fine for the fixture, not a production hash.
- Mayo’s appointment confirmation code is `MAYO-` plus a hash of email and date, so it can be computed without the site. The grader requires the stored row.
- SmartAsset calculator tasks are reproducible from `calc.py`. The graders require the calculator URL and the figures the page actually shows (headline rounding, or the unrounded final-payment chip where the template prints it raw).
- SmartAsset--4 does not render a “deduction used” chip. The applied deduction is AGI minus taxable income, and the page states tax year 2025. Feasible, but the missing chip makes the task harder than the wording suggests.
- SmartAsset--9 leaves life expectancy (95) and Social Security ($2,200/month) at form defaults the prompt never names. The nest egg and the “not on track” result survive zeroing Social Security; the shortfall dollar amount does not. The grader asks for the nest egg and the negative on-track status, not the shortfall.
- SmartAsset--17 leaves Other assets at the form default of $5,000. The frozen reading is assets $758,500, liabilities $333,500, net worth $425,000. Zeroing that default yields $420,000 and fails.
- SmartAsset--12 and --13 share author Jeff White and a 5-minute reading time. Article bodies are generic filler; the distinction the tasks ask for is the dek. Feasible and thin.
- Fandom--8: the newest Hu Tao revision and the one before it are both `+60` bytes, so “added, +60” does not uniquely identify the newest edit.
- Mayo--11’s location filter is redundant: all four neurology doctors are Jacksonville-only. Mayo--12 lists that same department set, not an MS-specific panel.
- Media provenance is disclosed and incomplete on every site. See below. No image bytes are in this git branch.

## Media and licensing

Each site has a `NOTICE.md` that already says the provenance is incomplete. That disclosure is necessary and not sufficient for a public asset merge.

- Apartments.com: `u-photo-*` files are an Unsplash pool; other building photos are described as an Apartments.com harvest; avatars and manager logos have no manifest and no embedded license.
- Eventbrite: inherited event, city, organizer, and article images with no per-file manifest.
- Fandom: Marvel, Star Wars, and Genshin JPEGs, claimed as fair use. `asset_manifest.json` records source URLs. Article text is locally authored, not a CC BY-SA scrape. Fair-use claims for redistributed character images should be reviewed before the HF archive is merged.
- Mayo Clinic: Wikimedia Commons images used as illustrations, explicitly not clinical captures, without a complete per-file license manifest. Trials are synthetic (`SIM-MAYO-*`), documented in `trial_fixture_provenance.json`.
- SmartAsset: 85 Pexels article photos without per-file creator or license records. Advisor portraits are illustrative for fictional advisors. Advisors, firms, and ratings are fixture data.

Local `static/images/` directories are not in this checkout, so image bytes were not inspected. Fandom’s `test_asset_manifest_and_references` fails here solely because `static/images/mcu_avengers__endgame.jpg` is absent.

## Security

No user-controlled SQL string building turned up in the request handlers (Eventbrite `ALTER` names and Mayo test/migration `PRAGMA`s are constants). Open redirects on Apartments, Eventbrite, and Mayo reject scheme-relative and off-site `next` values. Secrets are the usual hardcoded development keys. The serious functional issue was Fandom writing `view_count` on GET; that commit is removed. Eventbrite and Mayo still lack CSRF on state-changing POSTs (nit above).

## Reset and registry

Runtime reset, after the edits in this branch: copy `instance_seed/<site>.db` to `instance/<site>.db`, import the app twice. Both boots matched the seed for all five.

| Site | md5 of the frozen seed, unchanged after two boots |
| --- | --- |
| apartments_com | `dec0bd35142b358069757d67b5682901` |
| eventbrite | `b4fe2a43cb85d343813c5c3b899f6679` |
| fandom | `df11fdd611144ac8f7a0dffd9ffc8de8` |
| mayo_clinic | `fea425c23cf2461977621ff3647dcd7f` |
| smartasset | `d6f750ba625100cb5cd36c2376bc5e9f` |

Internal registry on this head: 104 names, the five new sites last, ports `40099`–`40103`. `websyn_start.sh`, `control_server.py`, Dockerfile `EXPOSE`, and the README table agree. `.assets-revision` does not list the new bundles.

## Per-site notes

### Apartments.com (16 tasks, port 40099)

Auth works for `alice.j@test.com` / `Password123!`. Tour requests, reviews, and saved searches are real rows and are what the graders check. Student housing was the one catalog bug: a rating sort capped at 24 hid San Antonio and made a unique “winner” out of a 5–5 tie with New York. `/student-housing` now renders “42 Student Housing properties” and does not append “+”. Senior and military pages still cap at 24. Cards leak Walk Score and rent, which makes several browse tasks easier than a detail-page task.

### Eventbrite (18 tasks, port 40100)

Checkout, promo codes, likes, account city, and signup are real and covered by DB graders. Order codes are random, so the answer must echo the stored code; a memorized code fails. The West region page previously had no per-city counts (only a combined 60-event list), so task 17 was not answerable. It now prints the full upcoming count under each city. Smoke check of `/region/west`: the count 32 appears three times, 31 three times, 30 once, 27 once. Benchmark weekend math uses `2026-05-27`.

### Fandom (18 tasks, port 40101)

Wikis, history, categories, polls, watchlists, and forum threads are backed by the database. Three tasks are famous-knowledge shortcuts and should be replaced with fixture-only facts (Zhongli’s constellation “Lapidus”, the four-name Guardians category, and Arlecchino’s constellation are the right kind of anchor). Article and forum GETs no longer change the database; a smoke client confirmed Tony Stark and forum thread 1 return 200 and leave `fandom.db` byte-identical. Recent changes with `hide_bot=1` now says “200 revisions shown (page limit 200)”. Poll votes are not unique per user; Carol’s new Liyue vote moves the displayed count from 71 to 72, and the grader reads that stored total.

### Mayo Clinic (20 tasks, port 40102)

Symptom checker, doctor filters, trials, and the portal are coherent. Trial ids are synthetic. Task 10 is the hard feasibility miss (no byline). Task 0 should be re-anchored off the shared diabetes boilerplate. Appointment requests do not require login; the confirmation code is deterministic from email and date, and the grader requires the row (`test@example.com`, `2026-10-15`, code `MAYO-277547AF`). Alice’s portal confirmation `MAYO-A1B2C3D4` and five saved items are seed state.

### SmartAsset (18 tasks, port 40103)

Calculators are pure functions and the pages show rounded headlines via `commafy`, plus a raw final-payment chip on the credit-card calculator. A smoke POST of $5,000 / 22.5% / $200 rendered `$1,810` and `10.05`. Advisor filters return one California tax advisor (Karen Wright) and one Florida tax advisor (Nancy Gonzalez) at a $250,000 account-minimum cap; Florida is not empty. Saved calculations, registration, and logout are real. Logout then `/account` redirects to `/login`. The CD-deletion grader requires the label to have been observed, the row to be gone, and a login URL after logout, so “never saved” does not pass.

## Per-task feasibility

Verdicts describe the fixture as it stands on this review branch, including the four display fixes. “Shortcut” means a person who knows the real world can answer without the mirror; the grader still requires navigation, which is not a substitute for rewriting the task.

| Task | Verdict | Why |
| --- | --- | --- |
| Apartments.com--0 | Feasible | Miami EV-charging count is a labeled total and is unique to that filter. |
| Apartments.com--1 | Feasible | One cheapest Brickell 2BR at or below $3,500. Rent is bound to that building. |
| Apartments.com--2 | Feasible, card leak | Walk Score and available-unit count are on the card as well as the detail page. |
| Apartments.com--3 | Feasible, card leak | Both Walk Scores and both rent ranges are on the cards. Swapping the buildings fails. |
| Apartments.com--4 | Feasible | One cheapest available SF 1BR with dogs and in-unit laundry. |
| Apartments.com--5 | Feasible | SoMa preset returns one building. Grader uses the matching-unit range shown on the card. |
| Apartments.com--6 | Feasible, stateful | Tour row plus the confirmation number stored for it. |
| Apartments.com--7 | Feasible, card leak | Highest-rated Streeterville building is the first sorted card. |
| Apartments.com--8 | Feasible | Nearest grocery is closer than the other grocery and is not a park. |
| Apartments.com--9 | Feasible, card leak | Cheapest LA luxury rooftop+pool result is identifiable from the sorted cards. |
| Apartments.com--10 | Feasible | One nearby school rated 8 or higher. |
| Apartments.com--11 | Feasible, stateful | Review row on The Symphony (not The Symphony Lofts) and the updated count. |
| Apartments.com--12 | Feasible, stateful | Alice already has one saved search; the account total includes the new one. |
| Apartments.com--13 | Feasible | One cheapest Seattle unit available on or before 2026-06-30 with parking. |
| Apartments.com--14 | Feasible | First displayed available unit; building deposit, not the unit deposit. |
| Apartments.com--15 | Feasible after fix | Was a 24-item cap that hid the tie. Full catalog ties New York and San Antonio. |
| Eventbrite--0 | Feasible | One free NYC music event in the benchmark weekend window. |
| Eventbrite--1 | Feasible, stateful | GA qty 2 at the stored total. Order code is random and must be read back. |
| Eventbrite--2 | Feasible | The free tier makes AI Product Summit cheaper. A paid-tier comparison picks the wrong event. Prices are bound after the event name. |
| Eventbrite--3 | Feasible | Two June online business conferences. “The AI conference” selects AI Product Summit’s first speaker. The e-commerce workshop is the distractor. |
| Eventbrite--4 | Feasible | One Austin in-person music event at or below the stated cap. |
| Eventbrite--5 | Feasible | One NY arts event whose refund policy is the flexible label, with a stable start date. |
| Eventbrite--6 | Feasible, wording nit | Both tiers are sold out. The prompt says “tier” singular. Grader requires both. |
| Eventbrite--7 | Feasible | Three tiers; the expensive one and the timezone are on the event page. |
| Eventbrite--8 | Feasible | Stable `DTSTART` and location. `DTSTAMP` is not stable. |
| Eventbrite--9 | Feasible | Refund help search returns four articles. |
| Eventbrite--10 | Feasible | Music pills from Rock through Hip Hop are an ordered triple. |
| Eventbrite--11 | Feasible | Author and the published date are on the post. |
| Eventbrite--12 | Feasible, stateful | Saved-event row for the named event. |
| Eventbrite--13 | Feasible, stateful | Free order with the dietary note and a stored code. |
| Eventbrite--14 | Feasible, stateful | Promo discount is stored on the order. The paid total depends on what was purchased, so the grader checks that order rather than one hardcoded total. |
| Eventbrite--15 | Feasible, stateful | Alice’s city changes from the seed value. |
| Eventbrite--16 | Feasible, stateful | New account row. The password is hashed, so the grader checks identity, not the secret. |
| Eventbrite--17 | Feasible after fix | Per-city counts were missing. West ties three cities. |
| Fandom--0 | Shortcut, send back | Tony Stark’s birthday is famous. |
| Fandom--1 | Feasible | The species string is fixture-specific. Deceased status alone would be famous. |
| Fandom--2 | Feasible | Constellation text differs from the usual canon name. Version is bound to Zhongli. |
| Fandom--3 | Shortcut, send back | Purple blade and Vaapad are famous. |
| Fandom--4 | Feasible | The category lists four people. Extra Guardians fail. |
| Fandom--5 | Feasible | Arlecchino’s element, weapon, region, and constellation. Childe is the near-miss. Five-star weapons sit in the same category. |
| Fandom--6 | Feasible after fix | Answer is the 200 rows shown, not the 245 non-bot revisions in the table. The heading now says so. |
| Fandom--7 | Feasible | History length is printed on the page. |
| Fandom--8 | Feasible, weak | Newest and previous deltas are both +60, so the sign is not a unique newest-edit signal. |
| Fandom--9 | Shortcut, send back | Tatooine’s moon count is famous. |
| Fandom--10 | Feasible, stateful | New user with no edits. Avatar color is random and is not graded. |
| Fandom--11 | Feasible, stateful | Watch row is not pre-seeded. |
| Fandom--12 | Feasible, stateful | Revision summary and the new sentence must both be stored. |
| Fandom--13 | Feasible, stateful | Grader reads the Liyue total after the new vote. Users may vote more than once. |
| Fandom--14 | Feasible | What-links-here is a fixed article set. A short list of unrelated pages fails. |
| Fandom--15 | Feasible | Reply count is bound to the named pinned thread. The other pinned thread has a different count. Opening it no longer writes `view_count`. |
| Fandom--16 | Feasible | One active poll question per wiki. |
| Fandom--17 | Feasible | The cathedral file’s uploader is distinct from the concept-painting uploader. |
| Mayo Clinic--0 | Shortcut, send back | Shared boilerplate prevention text, also answerable from general knowledge. |
| Mayo Clinic--1 | Feasible | Four named drugs. A related condition’s drug is a distractor. |
| Mayo Clinic--2 | Feasible | Adult acute chest pain surfaces pulmonary embolism as urgent. |
| Mayo Clinic--3 | Feasible | Chronic adult fatigue lists several routine causes; the grader requires a majority of them. |
| Mayo Clinic--4 | Feasible | Both procedures are Orthopedics. Name lookalikes in other departments fail. |
| Mayo Clinic--5 | Feasible | One Jacksonville cardiologist who lists Spanish. |
| Mayo Clinic--6 | Feasible | One trial id and intervention. Ids are synthetic. |
| Mayo Clinic--7 | Feasible | Indication, side effects, and warning are on the drug page. |
| Mayo Clinic--8 | Feasible | CABG is tied to coronary artery disease and to the department’s display name. |
| Mayo Clinic--9 | Feasible, stateful | Code is computable, so the grader requires the appointment row. |
| Mayo Clinic--10 | Not answerable as an author | No author field and no byline. Honest “no byline” plus category is the only pass. |
| Mayo Clinic--11 | Feasible | Count is the full Jacksonville neurology list. The location filter adds nothing. |
| Mayo Clinic--12 | Feasible, loose | Doctors are the neurology department, not an MS-only panel. |
| Mayo Clinic--13 | Feasible | Phase 2 + Recruiting + Rochester is a stable count. Location match is “contains Rochester.” |
| Mayo Clinic--14 | Feasible | One of the four named drugs is absent. Saying a present drug is missing fails. |
| Mayo Clinic--15 | Feasible | Imaging category and letter M produce a fixed set. |
| Mayo Clinic--16 | Feasible | One trial is linked through that department’s doctors. |
| Mayo Clinic--17 | Feasible | The interaction warning is on the page. The long description is generic. |
| Mayo Clinic--18 | Feasible | The woodworking detail is synthetic and page-specific. Other patient stories are distractors. |
| Mayo Clinic--19 | Feasible, read-only | Portal shows the seed confirmation code and the saved-item count. |
| SmartAsset--0 | Feasible | Months, rounded interest, and the raw final payment are on the result. |
| SmartAsset--1 | Feasible | Each payment is bound to its own months and interest. Swapping them fails. |
| SmartAsset--2 | Feasible | Month savings are exact. Interest savings accept the rounded chip difference and the precise difference. |
| SmartAsset--3 | Feasible | Final balance, deposits, and interest are separate chips. |
| SmartAsset--4 | Feasible, derived | Deduction used is not labeled. It is the standard deduction, which beats the itemized input. Tax year is on the page. |
| SmartAsset--5 | Feasible | Each state is bound to its own estimate, plus the limitation notice. Swapping states fails. |
| SmartAsset--6 | Feasible | Per-paycheck net and annual take-home for the stated filing, state, and pre-tax inputs. |
| SmartAsset--7 | Feasible | Both directions are bound to the destination city. Index numbers are not rendered; the percent and direction are. |
| SmartAsset--8 | Feasible | Principal-and-interest is distinct from the total monthly payment. |
| SmartAsset--9 | Feasible, defaults | Nest egg and “not on track” under the form’s untouched life-expectancy and Social Security defaults. |
| SmartAsset--10 | Feasible | One matching California advisor, with name, firm, rating, and minimum. |
| SmartAsset--11 | Feasible | One matching Florida advisor. An empty-result answer fails. |
| SmartAsset--12 | Feasible, thin | Author, reading time, and the dek’s standard-versus-itemize line. Body text does not add the distinction. |
| SmartAsset--13 | Feasible, thin | Same author as task 12. The tax-timing line is the dek. Author alone fails. |
| SmartAsset--14 | Feasible, stateful | New user, not a seed account, and one saved credit-card row with those inputs. |
| SmartAsset--15 | Feasible, stateful | Alice’s saved savings row and its summary. |
| SmartAsset--16 | Feasible, stateful | Row must be observed and then absent. Logout must be followed by the sign-in page. |
| SmartAsset--17 | Feasible, defaults frozen | Other assets stay at the form default. The zeroed-default net worth fails. Assets and liabilities are bound separately. |

## Grading contract

Primary grader is the deterministic script. The LLM judge is secondary and only sees the rubric.

```bash
python3 -m unittest discover -s sites/<site>/verify -p 'test_*.py'
```

`eval_judge.py --verifier True` runs `sites/<site>/verify/verify_N.py --run_dir <dir>`. Stateful tasks also read `initial_state.db` and `after_state.db` in the run directory when those paths are not passed explicitly. Each package’s tests cover an empty answer, a correct answer with no navigation, a wrong answer on the right URLs, a correct self-report with an unchanged database, and a passing trajectory. Extra cases reject same-number/wrong-entity answers (Apartments rent, Eventbrite prices, SmartAsset swapped payments, states, cities, and the zeroed net-worth default, Fandom extra Guardians, Mayo a present drug called missing).

## What was run

Ran:

- Byte-identical reset of all five frozen seeds: copy seed to `instance/`, import the app twice, compare md5. All five matched, including after the GET-write and template fixes.
- Scratch rebuild from an empty database at `PYTHONHASHSEED=0` for all five, then a column-level diff against the frozen seed. Only Apartments.com matched byte-for-byte. Diffs are in the blocking section.
- Verifier unit tests: Apartments.com, Eventbrite, Fandom, Mayo Clinic (each `OK`), SmartAsset (`OK`, including swap cases).
- Site suites: Apartments.com 13 OK, Eventbrite 16 OK, Mayo Clinic 11 OK, SmartAsset workflow tests 9 OK, SmartAsset calculator tests 12 OK. Fandom 12 OK and 1 failure: `test_asset_manifest_and_references`, missing `static/images/` (assets not fetched).
- Flask test-client smoke on temporary copies: `/student-housing` renders “42 Student Housing properties” without a trailing “+”; `/region/west` shows the tie counts; Fandom article and forum GETs leave the DB unchanged and recent changes shows the 200-row label; the Mediterranean-diet article contains “Nutrition” and does not contain “author”; credit-card calculator POST shows `$1,810` and `10.05`.
- `python3 -m py_compile` on the edited app modules.
- Open-PR port check via the GitHub API for #225, #231, #232, #236, #240, #241, #242, #243, #244, and #245 (SITES length and `EXPOSE`).
- HF discussion #144 API: `status` is `open`.

Not run:

- Docker image build, control-plane `/health`, the full 104-site HTTP loop, and `/reset` inside a container. No Docker daemon in this environment.
- Playwright and `agent_demo` trajectories. No browser pass over the rendered UI beyond Flask test clients. Image pixels were not reviewed because `static/images/` is not in the checkout.
- A fresh `./scripts/fetch_assets.sh`. Local seeds were already present and are gitignored; they were not committed.

## Merge order

1. Merge HF discussion #144 (or a reviewed replacement archive), then set `.assets-revision` to that merged commit and fetch clean.
2. Re-slot these five sites to whatever indexes are actually free after the Porsche / StubHub / SourceForge / SpotHero / Student.com / Statista queue, and update all four registry surfaces together.
3. Replace or re-anchor Fandom--0, Fandom--3, Fandom--9, Mayo Clinic--0, and Mayo Clinic--10 before calling the task set accepted.
4. Land this review branch’s verifiers and the four display fixes with the contributor code. Do not regenerate the four non-deterministic seeds in Docker until the bcrypt and `utcnow` defaults are pinned.
