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
- Query timeout: 5 s default, enforced with SQLite's progress handler (`connect(timeout=)` only covers lock waits, not slow queries). Timed-out queries score 0. (Open: confirm 5 s is enough for all gold queries.)
- Status per example: correct / wrong_rows / no_sql / error / timeout / gold_error.
- Gold query runs first. If it fails, the example is marked gold_error: excluded from accuracy, skipped in GRPO, and investigated if more than one or two.
- Row comparison is set-based, so `1` and `1.0` count as equal.
- False-positive example: on BIRD dev q0, `SELECT 1` matches the gold answer (1.0). A concrete case of execution accuracy rewarding a meaningless query.

## GRPO reward
- 1.0 rows match, 0.1 runs but wrong, 0 error or no SQL. Kept small to limit reward hacking.