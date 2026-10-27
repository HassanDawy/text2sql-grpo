# Notes and decisions

## Data
- BIRD dev: 1,534 questions, 11 databases.
- Schema = raw `CREATE TABLE` text from `sqlite_master`, skipping SQLite's internal `sqlite_` tables. Kept as-is for now, including comments and alignment spaces. (Open: normalize whitespace?)

## Prompt (v1, frozen)
- System prompt: SQLite expert, exactly one query, only schema tables/columns, answer in a ```sql block.
- User message: schema, then hint (BIRD evidence), then question, each under a `###` label.
- Empty evidence → "None", so every prompt has the same three sections.
- Same prompt for every stage and for GPT-4o-mini.

## Evaluation
- SQL extraction: first ```sql block only; no block = format failure. (Open: fallback for bare SELECT.)
- Failures recorded by type: no SQL found / SQL error / wrong rows.
- BIRD headline uses the official set-based comparison; a stricter ORDER BY version is reported separately.
- BIRD dev is used both for decisions and for reporting, as in the papers; disclosed in the write-up.
- Databases opened read-only (`mode=ro`), so model SQL can't modify BIRD data.
- Query timeout: 30 s, enforced with SQLite's progress handler. Gold check on BIRD dev: 1,532/1,534 correct at 5 s; the 2 failures were slow gold queries (q596: 10.0 s, q646: 6.4 s on laptop), not bugs. At 30 s (3× the slowest, extra margin for RunPod), all 1,534 pass. Same timeout for gold and predicted queries.- Status per example: correct / wrong_rows / no_sql / error / timeout / gold_error.
- Gold query runs first. If it fails, the example is marked gold_error: excluded from accuracy, skipped in GRPO, and investigated if more than one or two.
- Row comparison is set-based, so `1` and `1.0` count as equal.
- False-positive example: on BIRD dev q0, `SELECT 1` matches the gold answer (1.0). A concrete case of execution accuracy rewarding a meaningless query.

## Scoring engine
Python 3.8.10, SQLite 3.35.5, for every number in the results table. SQLite 3.49.1 (Python 3.13) returns the same rows but is far slower on some gold queries (q518: 0.1 s → 156 s; q701: 0.2 s → >600 s). On the pod (Linux), Python uses the OS’s SQLite, so if training gold queries hit this, cache gold rows from the laptop.

## GRPO reward
- 1.0 rows match, 0.1 runs but wrong, 0 error or no SQL. Kept small to limit reward hacking.

## Results
### GPT-4o-mini (gpt-4o-mini-2024-07-18), BIRD dev (dev_20240627), temperature 0
- Execution accuracy: 50.5% (774/1,534); simple 57.9%, moderate 39.9%, challenging 36.6%
- Status: 774 correct, 681 wrong_rows, 74 error, 5 timeout, 0 no_sql, 0 gold_error
- Cost: $0.26 total, $0.171 per 1,000 queries (avg 930 tokens in, 53 out)

### Qwen2.5-Coder-1.5B-Instruct, zero-shot, BIRD dev, temperature 0, max 512 tokens (vLLM)
- Execution accuracy: 26.5% (406/1,534); simple 33.2%, moderate 17.2%, challenging 13.1%
- Status: 406 correct, 398 wrong_rows, 718 error, 8 no_sql, 4 timeout, 0 gold_error
- 29 outputs hit the 512-token cap (all 8 no_sql are among them)
- Main failure mode: SQL that errors (47%), vs 5% for GPT-4o-mini. Decision: no extraction fallback; format failures are negligible.

## Analysis
### Zero-shot Qwen error analysis (dev)
718 errors; 621 (86%) are no such column. Of those: 556 reference a real column through the wrong table alias, 41 use a wrong or invented name (mostly near-misses), 22 rewrite awkward names in snake_case (e.g. FRPM_Count for FRPM Count (K-12)), 2 miss quotes. Other errors: 28 no such function, 14 ambiguous column, 8 no such table, ~30 syntax. Takeaway: schema grounding (which table owns which column) is the main failure, not SQL syntax. Re-run on SFT outputs to see what changes.


## Repo and environments (Oct 25–27)

- Reorganized into `text2sql/` (data.py, evaluate.py) + `scripts/`; editable install via `pyproject.toml` (`pip install -e .`).
- Laptop venv: Python 3.8.10, SQLite 3.35.5. Used for all scoring.
- Pod venv: Python 3.12.3 (used for verifiers, vLLM, training).
- `text2sql/` must stay Python 3.8-compatible (laptop imports it).
- Train support: `load_examples(json_path, db_dir)`; train has no question_id, so we use position in train.json (stable as long as train.json is unchanged).
- `get_schema` opens databases read-only, same as `execute_sql`.

## Scoring engine

- All results-table numbers are scored on SQLite 3.35.5.
- SQLite 3.49.1 (Python 3.13 on Windows) returns the same rows but is much slower on some gold queries: q518 0.1 s → 156 s; q701 0.2 s → >600 s. Likely a query-planner change.
- On Linux, Python uses the system SQLite (pod image: 3.45.1). Built SQLite 3.35.5 from source in /workspace/sqlite-3.35.5 (CFLAGS with -DSQLITE_ENABLE_DESERIALIZE) and loaded it via LD_LIBRARY_PATH in env.sh. Pod now reports 3.35.5.

## Zero-shot Qwen error analysis (dev)

- 718 errors; 621 (86%) are `no such column`. Of those: 556 real column via wrong table alias, 41 wrong/invented name (mostly near-misses), 22 awkward names rewritten in snake_case (e.g. FRPM_Count for `FRPM Count (K-12)`), 2 missing quotes.
- Other errors: 28 no such function, 14 ambiguous column, 8 no such table, ~30 syntax.
- Takeaway: schema grounding (which table owns which column) is the main failure, not syntax. Rerun scratch/column_errors.py on SFT outputs.

## BIRD train data

- Train: 9,428 questions, 69 databases (70 folders; one unused). Dev: 1,534 questions, 11 databases.
- Train/dev database overlap: none (verified).
- check_gold on train (SQLite 3.35.5, 30 s timeout, 5,211 s): 9,051 correct, 377 gold_error.
  - 208 no such column, 142 no such table, 23 timeout, 4 RIGHT/FULL OUTER JOIN (unsupported before SQLite 3.39).
  - All 377 excluded from SFT and GRPO. List: results/check_gold_train_failures.txt.

## verifiers v1 environment (environments/bird_sql)

- verifiers v1 does not run on native Windows (imports `fcntl`). Develop and test on the pod.
- Scaffolded with `vf-init bird-sql`; installed with `pip install -e environments/bird_sql`.
- `TaskData.prompt` accepts a message list, so prompt v1 (`build_messages`) is used unchanged.
- `BirdSqlData`: question_id, db_id, gold_sql, difficulty (None for train). Stores db_id, not db_path (paths are machine-specific).
- Reward: wraps `evaluate_one`; runs it with `asyncio.to_thread` (it's blocking, up to 30 s); finds the database in the dev folder, then train (safe because no overlap); raises on gold_error instead of returning a number.
- `load()`: split = dev | train; drops IDs listed in the split's failures file; optional num_tasks.
- `text2sql` is not listed in the environment's dependencies (not on PyPI). Revisit for Week 4 publishing.
- Checks passed: 1,534 dev tasks, 9,051 train tasks; reward gives correct/1.0, wrong_rows/0.1, no_sql/0 on both splits.

## Reward hacking risks (decide before GRPO)

- wrong_rows earns 0.1: a trivially safe query can earn partial credit. Watch for wrong_rows rising while correct stays flat.
- `SELECT 1` scored correct (1.0) on dev q0: gold answer is (1.0,), and 1 == 1.0 in the set comparison (same as BIRD's official script).
- Same risk for gold answers that are empty (any query returning no rows matches). Need to count empty and single-0/1 gold answers on train before GRPO.

## RunPod lessons (new)

- Container disk is wiped on stop; only /workspace (volume) persists. Reinstall tmux after each restart.
- Network volume: `df` shows the whole storage cluster (e.g. 210T), not your quota.
- Right after starting, the volume may not be fully mounted. If files look missing, wait a minute and check again.
- BIRD zips contain __MACOSX junk folders; delete them.
- `tar` on the volume: use `--no-same-owner`.
- Run long jobs in tmux (detach: Ctrl+B, D; reattach: `tmux attach -t <name>`).

## Week 2 to-do

- Measure the longest train prompt in tokens before choosing SFT `max_length`.


## Related environments (checked 2026-10-23)
- verifiers v0.4.0 (Oct 2026) removed the v0 stack; our environment targets v1.
- sql-single-turn (stelioszach, Apache-2.0, v0): synthetic templated schemas; ordered result-set equality. Source repo archived Jul 2026.
- skyrl-sql (primeintellect, MIT, v0): multi-turn, SkyRL-SQL protocol; 653 train samples (SynSQL + Spider), Spider eval; reward -1 format / 0 wrong / 1 correct.
- Neither targets BIRD or v1. Ours: v1, single-turn, BIRD, execution-match reward with failure categories. Cite both.
- Stretch goal is not novel: multi-turn RL text-to-SQL exists (SkyRL-SQL and its Hub env).