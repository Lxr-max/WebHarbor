# Review: SourceForge (PR #240)

Reviewed September 28, 2026. Upstream contribution: [aiming-lab/WebHarbor #240](https://github.com/aiming-lab/WebHarbor/pull/240) by @Raibows (`b8ca008`, `raibows <raibows@hotmail.com>`), parent `1c1dc23f`. This report is the Track B review. It does not comment on #240.

The review host ran the site as a standalone Flask process, the same import the container supervisor uses (`from app import app`). Docker's API is reachable at `tcp://127.0.0.1:2375` (server 29.1.4). `/var/run/docker.sock` is not present. The multi-site image was not built: the other sites' Hugging Face archives are not in this checkout. Live `sourceforge.net` returned a Cloudflare challenge, so visual comparison uses the mirror's own pages and the harvested SourceForge chrome, not a fresh side-by-side.

## Review: sourceforge

### Mechanical checks: FAIL

- [ ] All registered sites return 200. Only SourceForge was started. Its navigated routes returned 200 (home, directory, project, reviews, files, stats, bugs, forums, wiki, news, software, about, auth, registration).
- [ ] Control plane `/health`, `/reset`, `/reset-all` were not run. No multi-site container was started.
- [x] Byte-identical boot on the production import path, before any writes. `instance/sourceforge.db` and `instance_seed/sourceforge.db` both md5 `6bfce1486a55e653df7683e4be041156`. Schema digest `aa61b172…` and rows digest `520501ac…` match the frozen verifier contract. The file hash differs from the hash advertised on #240; that difference is the host SQLite byte layout (3.45.1), not the logical rows. A second seed rebuild on this host matched the first file.
- [ ] Parallel reset was not run.
- [ ] Hugging Face pin. `.assets-revision` is still `5d2b17fa21067990370f8e7fc27123a1c24d7802` and does not contain this site. Images came from unmerged dataset PR #145 (`refs/pr/145`). `sourceforge.tar.gz` sha256 `4ad55e10548c17c3d326638c18d4a4eeec10c549c30afc31312dc0faa26ecc52` matched the download (38,458,817 bytes, 1,090 image files).

`python3 -m py_compile sites/sourceforge/app.py sites/sourceforge/seed_data.py` succeeded. `pytest sites/sourceforge/verify/tests/test_verifiers.py`: **233 passed**.

`python app.py` crashes. `seed_data.py` imports `app` as a second module while `__main__` is already `app.py`, so the seed query hits a different SQLAlchemy instance. `site_runner.py` starts `from app import app`, and that path boots and keeps the seed bytes identical. The container entry point is fine. A direct `python app.py` is not.

### Slot (documented, not renumbered)

`sourceforge` is appended after `ryanair`. Index **99**, container port **40099**. The README websites table, the README port range, `Dockerfile` `EXPOSE 40000-40137`, `tasks.jsonl` `web` values, and `app.py`'s default `PORT` all say **40137**. Open PR #239 occupies **40099–40103**. This review does not change any of those numbers.

### Visual fidelity: PASS

- [x] Homepage uses the SourceForge sandiego chrome: orange logo, top utility bar, Business Software / Open Source Software / Podcast nav, green search, Staff Choice and Community Choice, project icons, and a dark footer with the San Diego headquarters address.
- [x] Directory, project, reviews, files, bugs, forums, business-software, and login pages use the same chrome, green primary buttons, and real project icons and screenshots. Home had 18 images and the 7-Zip project page 11; none were broken or tiny placeholders.
- [x] Login is the classic two-column SourceForge form. The bugs page is an Allura-style tracker with a summary sidebar. The forum index is a topic table. The CRM directory is a card grid with ratings.
- [x] 1280, 768, and 390 viewports: homepage `scrollWidth` equals `clientWidth` (overflow 0). At 390px the header collapses to a menu button.
- [ ] Fresh side-by-side with sourceforge.net. The live site returned Cloudflare "Attention Required" and was not compared pixel for pixel.

Screenshots: `/opt/cursor/artifacts/pr240-sourceforge/01-home-desktop.png`, `03-home-mobile.png`, `06-directory-popular.png`, `07-project-7zip.png`, `08-reviews-7zip.png`, `13-bugs.png`, `15-forums.png`, `17-crm.png`, `21-login.png`.

### Functional depth: PASS

- [x] Login with `alice.j@test.com` / `TestPass123!` lands on `/` and the account page shows Alice Johnson. A wrong password stays on `/auth/` with "Invalid username or password."
- [x] Search and the Sort By menu. Clicking Sort By → Most Popular navigates to `?sort=popular`. `file compression` shows 96 projects, `video player` 53, `CRM` sorted by rating 2, `erp` sorted by rating 8, Games 26.
- [x] Bookmark add, reload, and remove persist. A 5-star review with an empty body is blocked in the browser ("Please fill out this field."); a filled review is stored and appears on the account page.
- [x] Profile edit to display name "Alice Review" and country Germany survives reload.
- [x] Registration rejects a malformed email in the browser and, with HTML5 validation bypassed, rejects it on the server. With the Terms checkbox checked, `fleet-admin` / `fleet-admin@example.com` / `LongPass123!` / Germany creates the account, Edit Profile saves, and bookmarking CrystalDiskInfo shows on the account page. My Reviews for that new user says "You haven't written any reviews yet." Headings are "My Account" and "Edit Profile".
- [x] Bob (`bob.c@test.com` / `TestPass123!`) starts with WinSCP and CrystalDiskInfo. Removing CrystalDiskInfo, bookmarking Ventoy, and posting a 4-star review that mentions USB sticks leaves WinSCP and Ventoy, drops CrystalDiskInfo, and shows the review.
- [ ] Help and Open Discussion advertise **8,276** and **29,076** topics on the forum index, and only **25** threads are stored in each forum. The thread page does not repeat the advertised total. Tasks 4 and 14 still have a number on the page, and the verifier accepts either 25 or 8,276, so grading does not deadlock. The two surfaces disagree.
- [ ] PortableApps.com `review_count` is 266 on the project page. The Reviews histogram is 251 / 7 / 0 / 2 / 4, which sums to 264, and the Reviews page never shows 266.

### Task quality: PASS

Directory cards show weekly downloads, review count, and last-update date. License, registered date, numeric average rating, ticket text, and forum quotes are not on the cards. No task is fully answerable from a listing alone. Counts below are what the live pages contained.

| Task | Result | Evidence |
|---|---|---|
| 0 | PASS | Popular search lists MinGW then AutoClicker. Project pages show 3,600,000 / 768,800 / 23,587, the registered dates, and the licenses. 7-Zip Reviews shows 4.8, 171 is on MinGW's reviews, 831 is the 7-Zip total. Weekly counts and last-update dates are also on the cards. |
| 1 | PASS | `7-Zip/26.03` and `26.02` list the named builds. Folder weeklies 29,589 and 21,750 are on the parent version list, not inside the folder. Download page names `7z2603-x64.exe`. Timeline peak 2026-09-19 / 6,001. OS table Windows / 90,456. |
| 2 | PASS | 7-Zip reviews: 4.8, histogram 765 and 27, featured review by itreet-raking5. Filter dropdown opens and `?filter-stars=4` is a real link. KeePass page shows 606 reviews. |
| 3 | PASS | Ticket 2701: "user interface misleading", Harry Stein, status open, priority 5, owner reply about a slow USB drive. CVE search lists 2681, 2670, and 2669. Ticket 2669 shows Igor Pavlov and 2026-06-10. Sidebar open count is on the tracker. |
| 4 | PASS | Dark Mode (Carlos Nunes, eye-comfort quote), Dark Theme (kb0000001), and 7-Zip 26.02 (297,148 views) are on the Open Discussion list. View counts are on the list, not repeated on the thread page. Help's labeled topic count is 8,276; the thread list has 25 rows. |
| 5 | PASS | Top page shows TrueType core fonts 3.3B, MinGW 3.6M, and 7-Zip. corefonts registered 2001-08-22. Notepad++ Plugin Manager weekly 109,095. |
| 6 | PASS | CRM category lists Pipedrive 3,120, SuiteCRM 1,150, EspoCRM 480, with full descriptions on the business pages. Open-source CRM search sorted by rating shows 2 results and Dolibarr first. Support recommends the project forums. |
| 7 | PASS | Logged in as Alice, bookmarked Password Safe, posted a 5-star "daily" review, saw both on the account page, and removed the bookmark. |
| 8 | PASS | Map: United States 40,718. WinSCP project page updated 2026-09-03. Same stats surfaces as task 1. |
| 9 | PASS | Games lists 26 and names DOSBox and Neko Void. Page 2 still says "Showing 26" and contains one card, "ii's Stupid Menu". DOSBox weekly 14,848. Top weekly #1 is MinGW. |
| 10 | PASS | Staff and Community choices are on the homepage. PortableApps.com page has weekly 422,400, registered 2005-10-21, MPL, and 266 reviews. Reviews page has rating 4.9 but not the number 266 (histogram sums to 264). KeePass weekly 205,800, updated 2026-07-25. |
| 11 | PASS | `video player` shows 53. Next Player and Video.js are in the results. Windows facet shows 13. Rating sort puts Shotcut first. Video.js summary on the project page is "Open source HTML5 video player". |
| 12 | PASS | Profile `ipavlov` shows joined 2000-08-17. p7zip registered 2004-06-12. 7-Far registered 2009-12-28. Summaries are real sentences, not nav chrome. |
| 13 | PASS | Registration, Germany, display name, CrystalDiskInfo bookmark, headings "My Account" / "Edit Profile", and the empty My Reviews sentence all worked. The form requires the Terms checkbox. |
| 14 | PASS | Wiki lists BZIP2 and the other formats. News has the 9.21 post. Support names forum 45797. Same forum surfaces as task 4. |
| 15 | PASS | Ticket 2681 shows "CVE-2026-58052", status open, Priority 7. Ticket 2669 has the owner and 2026-06-10. Open Discussion has the vulnerability-scanner thread by Robert Barcikowski. |
| 16 | PASS | SDK folder lists `lzma2601.7z` (1.8 MB, 2026-04-29, weekly 27). The folder weekly 675 and the root weekly 23,345 are on the parent file listing. `7z2600-x64.exe` is in 26.00. |
| 17 | PASS | KeePass weekly 205,800. Top page shows 430M and 191M. |
| 18 | PASS | Bob's bookmark swap from CrystalDiskInfo to Ventoy and the 4-star USB review persisted on the account page. WinSCP stayed. |
| 19 | PASS | Team page names Logan Abbott. NinjaOne ratings count 6,035. Google Cloud Platform 61,049. Footer has 1320 Columbia. `file compression` returns 96. About page has 1999 and 123,200. Podcast page has FastField and 2026-09-03. |
| 20 | PASS | ERP category shows Odoo 4,100. `erp` sorted by rating shows 8 results. PSeInt registered 2004-11-28. |

None of these are knowledge-only, human-in-the-loop, or date-relative. The deepened tasks (tracker, forums, top chart, maintainer profile, company pages) need several surfaces. Distractors exist: file compression returns 96 projects, video player 53, and the CVE list includes more than one ticket.

### Grading contract

Contributor verifiers and rubrics were already on the branch. This review audited them.

- Original `check_answer_number` / `check_answer_any` accepted a number anywhere, including as a substring (`10` inside `109,095`, `25` inside `2010-11-25`).
- Numbers, K/M/B abbreviations, and ISO dates must now be standalone tokens owned by the named subject. `make_verifiers.py` refuses to emit an unbound one. `verify_0.py` … `verify_20.py` were regenerated.
- Contributor `judge_rubric` values named the projects, counts, dates, and ticket ids. They are now rules-only checkpoints. `tasks.jsonl` still has `verifier_path` and `judge_rubric` and no `answer` key. Questions, `web` (`http://localhost:40137/`), and `upstream_url` are unchanged.
- Regression tests cover no-op, shortcut, wrong answer, state mismatch, read-only mutation, package tampering, swapped subjects, a weekly count credited to the wrong project, rank-as-substring, a date day used as a topic count, one priority reused for two tickets, and rubric leaks. 233 passed.

### Required fixes before an upstream merge

1. Reconcile the port. Runtime is 40099 and collides with #239. The README, EXPOSE, task URLs, and `app.py` default say 40137. This review does not renumber.
2. Merge Hugging Face dataset PR #145, then pin `.assets-revision` to that merged commit. An open-PR revision is not a pin.
3. Run the multi-site image: control-plane health, a `/reset/sourceforge` md5 match, and the all-site HTTP sweep. Those were not run here.

Non-blocking defects:

- Forum index topic counts (8,276 / 29,076) do not match the 25 stored threads.
- PortableApps.com review count 266 does not match its histogram sum 264, and 266 is not on the Reviews page.
- Directory cards reveal weekly downloads, review counts, and last-update dates. The rest of each comparison still needs a detail page.

### What was run

```text
hf download ChilleD/WebHarbor sourceforge.tar.gz --repo-type dataset --revision refs/pr/145
sha256sum sourceforge.tar.gz   # matches 4ad55e10…
WEBSYN_SKIP_BOOTSTRAP=1 PYTHONHASHSEED=0 python seed_data.py
python3 -m py_compile sites/sourceforge/app.py sites/sourceforge/seed_data.py
SOURCEFORGE_TEST_SEED_DB=.../instance_seed/sourceforge.db \
  pytest sites/sourceforge/verify/tests/test_verifiers.py -q
# 233 passed in 19.02s

# production import path, port 41099
python -c "from app import app; app.run(host='0.0.0.0', port=41099, ...)"
# md5 instance == instance_seed == 6bfce1486a55e653df7683e4be041156 before writes

# Playwright Chromium: visual, functional, and per-task fact walk
# screenshots in /opt/cursor/artifacts/pr240-sourceforge/
```

The secondary LLM judge was not run. No agent trajectory was graded with a live model. Verifier tests use the frozen honest fixtures plus the adversarial cases above.
