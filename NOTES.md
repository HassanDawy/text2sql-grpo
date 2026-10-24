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

## GRPO reward
- 1.0 rows match, 0.1 runs but wrong, 0 error or no SQL. Kept small to limit reward hacking.

## Related environments (checked 2026-10-23)
- verifiers v0.4.0 (Oct 2026) removed the v0 stack; our environment targets v1.
- sql-single-turn (stelioszach, Apache-2.0, v0): synthetic templated schemas; ordered result-set equality. Source repo archived Jul 2026.
- skyrl-sql (primeintellect, MIT, v0): multi-turn, SkyRL-SQL protocol; 653 train samples (SynSQL + Spider), Spider eval; reward -1 format / 0 wrong / 1 correct.
- Neither targets BIRD or v1. Ours: v1, single-turn, BIRD, execution-match reward with failure categories. Cite both.
- Stretch goal is not novel: multi-turn RL text-to-SQL exists (SkyRL-SQL and its Hub env).