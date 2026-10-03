# porsche deterministic task verification

Run each task through the visible UI from a fresh site state. Save `trajectory.json`, decodable before/after PNG screenshots, `initial.db` and `after.db`. Grade with:

```bash
python agent_demo/eval_judge.py --run_dir /path/to/run --verifier True
```

The verifier checks task identity, local origin, required content visits, requested facts and database outcomes. The initial snapshot must match the frozen seed. Research tasks preserve all rows; stateful tasks permit only the requested changes. Natural prose, bullets and tables are accepted within the deterministic parser's documented patterns. These checks do not provide unrestricted natural-language understanding.

Tasks 6, 12, 17, 18 and 19 save persistent state. Allowed tables preserve existing rows; selected options are checked against the frozen catalog. Task 2 checks each electric model’s own power and price. Task 14 distinguishes unpublished Sunday hours from closed hours.

Tests use portable local seed fixtures and separately labelled synthetic evidence. Build the seed with `seed_data.py` before running site and verifier tests.
