# Notes and decisions

## Contents
1. Data
2. Prompt (v1, frozen)
3. Evaluation
4. Scoring engine
5. Results
6. Analysis
7. SFT
8. GRPO reward and reward-hacking risks
9. verifiers environment
10. Related environments
11. Repo and environments
12. RunPod lessons
13. Open items

---

## 1. Data

### BIRD dev
- 1,534 questions, 11 databases.

### BIRD train
- 9,428 questions, 69 databases (70 folders; one unused).
- Train/dev database overlap: none (verified).
- Train has no `question_id`, so we use the position in train.json (stable as long as train.json is unchanged; rerun check_gold on train if BIRD is re-downloaded).
- check_gold on train (SQLite 3.35.5, 30 s timeout, 5,211 s): 9,051 correct, 377 gold_error.
  - 208 no such column, 142 no such table, 23 timeout, 4 RIGHT/FULL OUTER JOIN (unsupported before SQLite 3.39).
  - All 377 excluded from SFT and GRPO. List: `results/check_gold_train_failures.txt`.

### Schema text
- Raw `CREATE TABLE` text from `sqlite_master`, skipping SQLite's internal `sqlite_` tables. Kept as-is, including comments and alignment spaces (decided; not normalized).

## 2. Prompt (v1, frozen)
- System prompt: SQLite expert, exactly one query, only schema tables/columns, answer in a ```sql block.
- User message: schema, then hint (BIRD evidence), then question, each under a `###` label.
- Empty evidence → "None", so every prompt has the same three sections.
- Same prompt for every stage and for GPT-4o-mini.

## 3. Evaluation
- SQL extraction: first ```sql block only; no block = `no_sql`. No fallback for bare SELECT (format failures are negligible; see Results).
- Status per example: correct / wrong_rows / no_sql / error / timeout / gold_error.
- Gold query runs first. If it fails, the example is gold_error: excluded from accuracy and skipped in training.
- Row comparison is set-based, like BIRD's official script (so `1` and `1.0` count as equal). A stricter ORDER BY version is reported separately.
- BIRD dev is used both for decisions and for reporting, as in the papers; disclosed in the write-up.
- Databases opened read-only (`mode=ro`), so model SQL can't modify BIRD data.
- Query timeout: 30 s, enforced with SQLite's progress handler; same for gold and predicted queries.
  - At 5 s, dev gold was 1,532/1,534; the 2 failures were slow gold queries (q596: 10.0 s, q646: 6.4 s on laptop), not bugs. At 30 s, all 1,534 pass.

## 4. Scoring engine
- Every number in the results table is scored on SQLite 3.35.5 (laptop: Python 3.8.10).
- SQLite 3.49.1 (Python 3.13 on Windows) returns the same rows but is much slower on some gold queries: q518 0.1 s → 156 s; q701 0.2 s → >600 s. Likely a query-planner change.
- On Linux, Python uses the system SQLite (pod image: 3.45.1). Built SQLite 3.35.5 from source in `/workspace/sqlite-3.35.5` (CFLAGS with `-DSQLITE_ENABLE_DESERIALIZE`) and load it via `LD_LIBRARY_PATH` in env.sh. Pod reports 3.35.5.

## 5. Results

### GPT-4o-mini (gpt-4o-mini-2024-07-18), BIRD dev (dev_20240627), temperature 0
- Execution accuracy: 50.5% (774/1,534); simple 57.9%, moderate 39.9%, challenging 36.6%
- Status: 774 correct, 681 wrong_rows, 74 error, 5 timeout, 0 no_sql, 0 gold_error
- Cost: $0.26 total, $0.171 per 1,000 queries (avg 930 tokens in, 53 out)

### Qwen2.5-Coder-1.5B-Instruct, zero-shot, BIRD dev, temperature 0, max 512 tokens (vLLM)
- Execution accuracy: 26.5% (406/1,534); simple 33.2%, moderate 17.2%, challenging 13.1%
- Status: 406 correct, 398 wrong_rows, 718 error, 8 no_sql, 4 timeout, 0 gold_error
- 29 outputs hit the 512-token cap (all 8 no_sql are among them)
- Main failure mode: SQL that errors (47%), vs 5% for GPT-4o-mini.

### Qwen2.5-Coder-1.5B-Instruct, SFT (LoRA r16), BIRD dev, temperature 0, max 512 tokens (vLLM)
- Execution accuracy: 44.4% (681/1,534); simple 51.8%, moderate 32.5%, challenging 35.2%
- Status: 681 correct, 658 wrong_rows, 195 error, 0 no_sql, 0 timeout, 0 gold_error
- 0 outputs hit the 512-token cap
- vs zero-shot: +17.9 points; errors 718 → 195 (−73%); wrong_rows 398 → 658 (queries now run but some have wrong logic)
- 88% of GPT-4o-mini's accuracy (44.4 / 50.5)
- Challenging > moderate is likely noise (n = 145, about ±8 points)
- Same generation settings as zero-shot; model = adapter merged into base (scripts/merge_lora.py)

### Qwen2.5-Coder-1.5B-Instruct, SFT + GRPO (LoRA r16), BIRD dev, temperature 0, max 512 tokens (vLLM)
- Execution accuracy: 47.5% (729/1,534); simple 54.7%, moderate 36.9%, challenging 35.9%
- Status: 729 correct, 644 wrong_rows, 161 error
- vs SFT: +3.1 points (+48 questions); errors 195 → 161 (−17%). Paired (McNemar): GRPO fixed 84, broke 36, p ≈ 1e-5.
- 94% of GPT-4o-mini's accuracy (47.5 / 50.5)
- Same generation settings as zero-shot and SFT; model = GRPO adapter merged onto the merged SFT model (scripts/merge_lora.py --base)
- Not comparable to SLM-SQL's SFT→RL gain (54.26 → 61.95): they use reasoning output and self-consistency over 16–64 samples; we use one greedy answer.

## 6. Analysis

### Zero-shot Qwen error analysis (dev)
- 718 errors; 621 (86%) are `no such column`. Of those:
  - 556 reference a real column through the wrong table alias
  - 41 use a wrong or invented name (mostly near-misses)
  - 22 rewrite awkward names in snake_case (e.g. FRPM_Count for `FRPM Count (K-12)`)
  - 2 miss quotes
- Other errors: 28 no such function, 14 ambiguous column, 8 no such table, ~30 syntax.
- Takeaway: schema grounding (which table owns which column) is the main failure, not SQL syntax.
- Script: analysis/column_errors.py --name zeroshot|sft|grpo.

### SFT error analysis (dev)
- 195 errors: 171 no such column, 13 no such table, 8 near "order" (likely an unquoted table named `order`), 2 no such function, 1 other.
- no such column breakdown (zero-shot → SFT): wrong table 556 → 150, wrong/invented name 41 → 14, mangled name 22 → 7, missing quotes 2 → 0.
- SFT cut every category by ~70% but didn't change the mix: wrong-table mistakes are still 88% of column errors.
- no such function 28 → 2 (stopped using MySQL-only functions).

### SFT: 20 wrong_rows failures by hand (random, seed 0)
- 9 benchmark issues (model arguably right): 5 hint contradicts gold, 2 gold selects unrequested columns, 2 gold logic wrong/questionable (e.g. q1247: OR/AND precedence bug in gold).
- 9 model mistakes: 4 schema/join, 3 ignored hint, 1 wrong aggregation, 1 date format (stored with time).
- 2 ambiguous questions.
- n = 20, so no percentage claims. Takeaway: part of wrong_rows is benchmark noise; the model sometimes loses by following hints literally. Same noise exists in train, so it's also GRPO reward noise.
- Script: analysis/sft_failures.py; labeled file: analysis/sft_failures.md.

### GRPO error analysis (dev)
- 161 errors: 133 no such column, 9 no such table, 8 near "order", 6 no such function, 5 other.
- no such column breakdown (SFT → GRPO): wrong table 150 → 113, wrong/invented name 14 → 13, mangled name 7 → 7.
- Mix unchanged: wrong table is 85% of column errors (88% after SFT). Almost all of the error drop is wrong-table mistakes.

### SFT → GRPO transitions (dev, analysis/transitions.py)
| SFT ↓ / GRPO → | correct | wrong_rows | error |
| --- | --- | --- | --- |
| correct (681) | 645 | 30 | 6 |
| wrong_rows (658) | 59 | 565 | 34 |
| error (195) | 25 | 49 | 121 |
- Fixed 84: 59 from wrong_rows, 25 from errors. Broken 36: 30 to wrong_rows, 6 to errors.
- 74 SFT errors left the error state, but only 25 became correct; 49 now run but return wrong rows. 40 new errors appeared (34 from wrong_rows, 6 from correct). Not reward hacking: wrong_rows earns 0, the same as an error.
- 645 of SFT's 681 correct answers stay correct.
- Any two models disagree on some questions by chance: individual cells are directions; the net +48 is what McNemar tests.

### SFT correct → GRPO wrong: all 36 by hand (analysis/grpo_broken.md)
- First-pass labels by Claude, spot-checked by Hassan: wrong table/join 10, wrong column 4, value format 4, ignored question 3, over-complicated 3, grouping/DISTINCT 2, ignored hint 1; benchmark issue 4, ambiguous 4, lucky SFT 1. n = 36, counts only.
- ~27 real model mistakes, mostly schema grounding (14 wrong table/join/column): the same weakness as the remaining errors. ~9 are not real regressions.
- GRPO follows hints more literally, even wrong ones: q964 ('America' vs data 'American'), q991 (copied the hint's typo 'forname'), q1458 (hint contradicts gold). 3 cases: an observation, not a finding.
- A few invented constants: q862 (raceId = 11 instead of year 2007), q481 ('Commander 2010'), q1479 (LIKE '%CZK').

### Comparison with SLM-SQL (paper setup, read 2026-10-28)
- SLM-SQL Qwen2.5-Coder-1.5B on BIRD dev: zero-shot 46.81, SFT 54.26, SFT+RL 61.95, +CSC-SQL 67.08. Ours: zero-shot 26.5, SFT 44.4.
- Not directly comparable: they use reasoning-first output (<think>/<answer>, "solve this step by step") and self-consistency over 16–64 samples (Appendix B; Table 3 labeled SC). We use one greedy answer, no reasoning. Their Figure 1 doesn't state its decoding; most likely the same SC setup.
- Their prompt comes from CSC-SQL; schema format not specified. SFT data: 916K synthetic examples with reasoning (SynSQL-Think-916K).
- Decision: keep prompt v1. Report the protocol difference; compare gains, not absolute numbers.
- Option (beyond MVP, decide in Week 4): also score the final model with self-consistency.
- Their GRPO reward: execution (1) + 0.1 × format. No partial credit for wrong rows. GRPO: lr 3e-6, 6 rollouts, 1 epoch on BIRD train.

## 7. SFT

### Data (`scripts/build_sft_data.py` → `/workspace/sft_data`, not in repo)
- BIRD train minus 377 gold_error minus works_cycles = 8,587 examples.
- Excluded works_cycles (464 examples; ~6.7k-token schema): 5% of examples but ~30% of tokens. Fits max_length 4096 and keeps GRPO prompts short.
- Each example: prompt v1 (`build_messages`) + assistant answer = gold SQL in a ```sql block (matches `extract_sql`).
- Random split (seed 0): 8,287 train / 300 val. Val shares databases with train, so it's for overfitting checks only, never for dev-style claims. Dev is never used for training or checkpoint selection.
- Tokens (prompt + answer): mean 857, p95 2,821, max 3,124. Dev prompt max: 2,209.

### Config (run 1: sft-lora-r16)- LoRA: r 16, alpha 32, all linear layers.
- Learning rate 2e-4, 2 epochs.
- Batch: 2 per step × 8 gradient accumulation = 16 effective (planned 4 × 4; halved per-step batch to limit memory from the 151k-vocabulary logits).
- max_length 4096 (no truncation), loss on the completion only, no packing.
- Gradient checkpointing, bf16.
- Tracking: Weights & Biases (key in repo `.env`, gitignored).
- Stack on pod: torch 2.14.1, transformers 5.21.0, trl 1.16.0, peft 0.21.2.

### Training run 1 (sft-lora-r16)
- Smoke test first (`--smoke`): 5 steps on the 40 longest examples; peak GPU memory 5.5 GB; trainable params 18.5M (1.18%).
- Verified loss is on the answer only: decoded labels contain only the ```sql answer.
- 1,036 steps, 66 min on an RTX 4090 (~3.8 s/step).
- Eval loss: 0.177 (step 100) → 0.128 (final), flat after step 900; no overfitting. Used `final`.
- Adapter: /workspace/checkpoints/sft_lora_r16/final; merged model: /workspace/models/sft_lora_r16_merged.
- W&B project text2sql-grpo, run sft-lora-r16.

## 8. GRPO reward and reward-hacking risks
- Original plan (superseded, see "Reward decision" below): 1.0 rows match, 0.1 runs but wrong, 0 error or no SQL.
- Risk: wrong_rows earns 0.1, so a trivially safe query can earn partial credit. Watch for wrong_rows rising while correct stays flat.
- Risk: `SELECT 1` scored correct (1.0) on dev q0. The gold answer is (1.0,), and 1 == 1.0 in the set comparison (same as BIRD's official script).
- Risk: gold answers that are empty match any query returning no rows.
- Trivial gold answers on train (`scripts/count_trivial_gold.py`, 2026-10-29; ids = positions in train.json, in `results/trivial_gold_train.json`). Excluding works_cycles, 8,579 gold queries run:
  - single 0 or 1: 297 (3.5%), matched by `SELECT 1` / `SELECT 0`
  - empty: 276 (3.2%), matched by any query returning no rows
  - single NULL: 45 (0.5%), matched by `SELECT NULL`
  - total: 618 (7.2%). Counts are on the pool before the train/val split.
  - Errors: 375 (385 including works_cycles) vs 377 in check_gold; the ~8 extra are likely queries near the 30 s timeout.
- Interpretation: `SELECT 1` everywhere would average ~0.13 reward (3.5% correct + 0.1 elsewhere), far below honest answers, so global hacking is unlikely. The risk is local: on uncertain yes/no or "how many" questions a trivial answer can win, and with 0.1 for wrong_rows any query that runs earns at least as much as an honest attempt that errors.
- Reward decision (2026-10-29): GRPO reward = 1.0 if rows match, 0 otherwise (option a). Dropped the 0.1 for wrong_rows: it made any runnable query at least as good as an honest attempt that errors. Kept the 618 trivial-gold questions: they're legitimate questions with real 0/1/empty answers, and removing them would bias training against those answers. Matches SLM-SQL (no partial credit for wrong rows). Safety net: monitor trivial_rate during training.
- `evaluate_one` stays unchanged (statuses still drive reporting); the GRPO reward lives in `text2sql/reward.py` (gold run once per question before parallel scoring, 120 s gold timeout, failed gold → question skipped via all-zero rewards).
- GRPO settings (planned, 2026-10-29): num_generations 6, temperature 1.0, lr 1e-5 (LoRA; SLM-SQL used 3e-6 full fine-tune), beta 0.04 (DeepSeekMath value; keeps the model near SFT on what the reward doesn't check, resists drift toward trivial queries; reference = adapter disabled, no extra memory), num_iterations 1 (clip inactive), max_prompt_length 3072, max_completion_length 512, 1 epoch, eval on the 300 val examples (never dev). Monitor: reward vs val accuracy, train/kl, error_rate, trivial_rate, completion length.

### GRPO run 1 (grpo-lora-r16-beta0.04, W&B run o56aq5j8, 2026-10-30)
- Data: `scripts/build_grpo_data.py` reuses the SFT split (no reshuffle → no val leakage). 8,279 train / 300 val; dropped 8 gold queries that timed out in the trivial-gold run (ids 5, 6, 7, 115, 1108, 2108, 3148, 3168). Max prompt 3,016 tokens.
- TRL 1.16 differences from the plan: no max_prompt_length setting (prompts never truncated); beta defaults to 0 (set 0.04 explicitly); loss_type defaults to "dapo" (kept: no length bias toward short answers like SELECT 1).
- Batch: 2 × 24 accumulation = 48 answers (8 questions × 6) per step; generation_batch_size 24 (48 ran out of memory on the longest prompts; 12 fit at 9.1 GB, 24 at 14.8 GB). 1,035 steps, 13.7 h on a 4090 (~38–48 s/step).
- Val accuracy (sampled, 2 answers per question): 0.57 at step 100 → 0.61 at 200 → ~0.64 by 700, then flat 0.61–0.64 (±2–3 points noise); final 0.63. Used `final`.
- No reward hacking: trivial_rate flat at ~0.12 the whole run; error_rate fell from ~0.17 to a few percent.
- Entropy collapse: entropy 0.105 → ~0.033 by step 400; frac_reward_zero_std 0.4 → ~0.75 (peaks 0.87). After ~step 400 only ~25% of groups carried signal, matching the val plateau. Most of the gain came in the first ~300–400 steps.
- Possible follow-ups (beyond MVP): higher temperature or more generations per question to delay the collapse.

## 9. verifiers environment (`environments/bird_sql`)
- verifiers v1 (0.4.0) does not run on native Windows (imports `fcntl`). Develop and test on the pod.
- Scaffolded with `vf-init bird-sql`; installed with `pip install -e environments/bird_sql`.
- Self-contained (2026-11-03): `bird_sql/core.py` copies the prompt v1 and evaluator code from `text2sql` (not on PyPI, and must stay Python 3.8; verifiers needs 3.11+). Keep the two in sync. The 377 train gold failures ship as `bird_sql/train_gold_failures.txt`.
- Data: `--env.taskset.data-dir` or `$BIRD_DIR` (dev) / `$BIRD_TRAIN_DIR` (train), pointing at the BIRD split folder. `--env.taskset.num-tasks` for a subset.
- `BirdSqlData`: question_id, db_id, db_path, gold_sql, difficulty (None for train).
- Reward `execution_match`: 1 if rows match, else 0 (same as GRPO training). Metrics (`@vf.metric`, recorded, not summed): `error` (SQL error, timeout, no SQL), `trivial` (empty or single 0/1/NULL result), `gold_error` (gold query failed; answer scores 0, no crash). Reward and metrics run concurrently, so each answer is scored once and shared.
- Gold rows cached per process; gold timeout 120 s, answers 30 s.
- At most one SQL query per CPU core (container quota from cgroup v2 `cpu.max` or v1 `cpu.cfs_quota_us`; override with `BIRD_SQL_WORKERS`). A query waits for a slot before its timeout clock starts, so a busy machine queues instead of timing out. Found on a 0.5-core CPU pod: 16 parallel queries made valid gold queries time out.
- Answers are streamed and compared to the gold set row by row: stop at the first row not in gold (wrong), otherwise keep only gold rows. Same result as BIRD's fetch-all set comparison (46k-pair randomized test, 0 mismatches) with memory bounded by the gold size. Replaced a row cap that wrongly failed q284 and q1059 (correct answers with huge numbers of duplicate rows) and two card_games gold answers over 100k rows.
- `scripts/check_env.py --name <run>` scores gold SQL and saved outputs through the environment, no model calls. On the 0.5-core pod: gold 1,533/1,534 (1 gold timeout at 120 s due to half a core). On a GPU pod (2026-11-04): gold 1,534/1,534; GRPO 729 correct / 161 error, 0 per-question disagreements with the pipeline.
- End-to-end run (2026-11-04, verifiers 0.4.1, vLLM 0.33.0). verifiers 0.4.1 has no `vf-eval`; the runner is `vf-run`. Its defaults are the `bash` coding-agent harness in a Prime cloud sandbox (needs a Prime login and adds a shell tool to the prompt). For this single-turn env use `--env.agent.harness.id null --env.agent.runtime.type subprocess`. Output: `<output_dir>/<run>/traces.jsonl`, one episode per line, with the scored trace inside `traces[]`.
- `vllm serve` applies the model's `generation_config.json` by default. Our merged models carry Qwen's `repetition_penalty: 1.1` (temperature/top_k/top_p too, ignored at temperature 0). First GRPO run with it: 698/1,534 (45.5%), identical text on only 969. Always start the server with `--generation-config vllm`. Offline `LLM` with explicit `SamplingParams` (gen_qwen.py) is not affected.
- Results (`scripts/compare_env_run.py <run_dir> <pipeline results>`): GRPO 733 (47.8%) vs pipeline 729; identical text 1,462/1,534 (95%); 6 outcome flips (5 up, 1 down), all with different text; 0 scoring disagreements on identical text. GPT-4o-mini (2024-07-18, temperature 0, no max tokens) 779 (50.8%) vs 774; identical text 1,196 (78%; API not deterministic); 37 flips (21 up, 16 down); 0 scoring disagreements. Headline numbers stay 47.5% / 50.5%: the env reproduces them within decoding noise.
- The repetition-penalty run also had 4 same-text scoring disagreements, all on card_games (q404, 410, 419, 420), cause not checked (possibly slow queries under load). They did not recur; watch for them in future runs.

## 10. Related environments (checked 2026-10-23)
- verifiers v0.4.0 (Oct 2026) removed the v0 stack; our environment targets v1.
- sql-single-turn (stelioszach, Apache-2.0, v0): synthetic templated schemas; ordered result-set equality. Source repo archived Jul 2026.
- skyrl-sql (primeintellect, MIT, v0): multi-turn, SkyRL-SQL protocol; 653 train samples (SynSQL + Spider), Spider eval; reward -1 format / 0 wrong / 1 correct.
- Neither targets BIRD or v1. Ours: v1, single-turn, BIRD, execution-match reward with failure categories. Cite both.
- Stretch goal is not novel: multi-turn RL text-to-SQL exists (SkyRL-SQL and its Hub env).

## 11. Repo and environments
- Layout: `text2sql/` (data.py, evaluate.py) + `scripts/` + `analysis/` + `environments/` + `results/`; `scratch/` gitignored.- Editable install via `pyproject.toml` (`pip install -e .`).
- Laptop venv: Python 3.8.10, SQLite 3.35.5. Used for all scoring.
- Pod venv (`/workspace/venv`): Python 3.12.3. Used for verifiers and training.
- `text2sql/` must stay Python 3.8-compatible (laptop imports it).
- `get_schema` and `execute_sql` both open databases read-only.
- Secrets in `.env` (gitignored): OpenAI key (laptop), W&B key (pod).

## 12. RunPod lessons
- Set a volume disk; only `/workspace` persists. The container disk is wiped on stop, so reinstall tmux after each restart.
- Use a venv in `/workspace` (system pip fails on Debian's PyJWT and is wiped on stop).
- `/workspace/env.sh`: activates the venv; sets BIRD_DIR, HF_HOME, LD_LIBRARY_PATH (SQLite 3.35.5).
- `df`, `nproc` and `free` show the whole host (e.g. 210T disk, 128 cores, 503 GB RAM), not the pod's share. Real limits: cgroup files (`/sys/fs/cgroup/cpu.max` or `cpu/cpu.cfs_quota_us`; `memory/memory.limit_in_bytes`).
- If the pod's GPU is taken, "Automatically migrate" moves the pod to a new machine; the volume data comes along.
- Right after starting, the volume may not be fully mounted. If files look missing, wait a minute and check again.
- BIRD zips contain `__MACOSX` junk folders; delete them.
- `tar` on the volume: use `--no-same-owner`.
- Run long jobs in tmux (detach: Ctrl+B, D; reattach: `tmux attach -t <name>`).
- git push needs a GitHub fine-grained token.
- Generate on GPU, score on laptop. Test scripts on `[:5]` first.
- The 100 GB volume filled up when installing vLLM ("Disk quota exceeded"). Deleted the BIRD zip files (all already extracted) to free space; use `pip install --no-cache-dir`.
- vLLM lives in its own venv (/workspace/venv-vllm) because it pins its own PyTorch; training stays in /workspace/venv.
- `deactivate` before deleting an active venv, then `hash -r`.
- Our data is on the pod's own volume disk, not a network volume (Storage page shows none). It's tied to one machine: when its GPUs are taken, the pod can't start on GPU or migrate. Never Terminate it. Next pod: use a network volume.
- "Start Pod using CPUs" works without a GPU but gives ~0.5 core and 512 MB RAM: fine for small checks, too small for full scoring runs.
- Adapters backed up (2026-11-03) to private HF repos hdawy/text2sql-qwen1.5b-sft-lora and hdawy/text2sql-qwen1.5b-grpo-lora (`hf upload ... --private`; GRPO needs `--exclude README.md`, since its auto README lists a local base path). The GRPO adapter sits on the merged SFT model. Losing the pod means about 1 h of rebuilding, no retraining.
- Pod migration (2026-10-29) emptied /workspace/venv; everything else survived. Rebuild: python3 -m venv /workspace/venv, then pip install --no-cache-dir torch==2.14.1 transformers==5.21.0 trl==1.16.0 peft==0.21.2 wandb "verifiers>=0.4.0", then pip install -e for the repo and environments/bird_sql.

## 13. Open items
- SLM-SQL reports Qwen2.5-Coder-1.5B zero-shot 46.81% vs our 26.5% (SFT: 54.26% vs 44.4%). Find their prompt/schema format and explain the gap before the write-up. Compare final results to their SFT+RL (61.95%), not CSC-SQL (67.08%).
- Optional, decide first: cost/serving benchmark (vLLM, needs the pod), e-commerce test set, self-consistency scoring.