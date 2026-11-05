# bird-sql

A verifiers v1 environment for single-turn text-to-SQL on [BIRD](https://bird-bench.github.io/). Each task is one BIRD question. The model gets the database schema, BIRD's hint ("evidence") and the question, and answers with one SQLite query in a ```` ```sql ```` block. The environment runs that query and the gold query on the real BIRD database and rewards the model when the returned rows match.

It is the evaluator and reward from [text2sql-grpo](https://github.com/HassanDawy/text2sql-grpo), where it was used to train Qwen2.5-Coder-1.5B-Instruct with SFT and then GRPO.

## Reward and metrics

| Name | Kind | Meaning |
| --- | --- | --- |
| `execution_match` | reward (weight 1) | 1 if the answer's rows equal the gold rows as sets (BIRD's official rule, so row order and `1` vs `1.0` don't matter), else 0 |
| `error` | metric | 1 if there was no ```` ```sql ```` block, the SQL failed, or it timed out |
| `trivial` | metric | 1 if the answer returned no rows or a single 0, 1 or NULL value |
| `gold_error` | metric | 1 if the gold query itself failed (the answer then scores 0) |

Metrics are recorded but not added to the reward.

**Why no partial credit.** An earlier design gave 0.1 for SQL that runs but returns wrong rows. That makes any runnable query at least as good as an honest attempt that errors, which invites reward hacking. The reward is binary, as in the SLM-SQL paper.

**Why `trivial` exists.** About 7% of BIRD train questions have a gold answer of a single 0/1, a single NULL, or no rows. On those, a query like `SELECT 1` scores 1. Track `trivial` during training: if it rises while accuracy stays flat, the policy is learning shortcuts.

## Setup

1. Download BIRD dev (and train if you need it) from the [BIRD site](https://bird-bench.github.io/) and unzip the databases, so the folder looks like:

   ```
   dev_20240627/
     dev.json
     dev_databases/dev_databases/<db_id>/<db_id>.sqlite
   ```

   BIRD data is not included in this package. Check BIRD's license before redistributing it.

2. Install the environment (Python 3.11+, Linux or macOS; verifiers does not run on native Windows):

   ```bash
   pip install -e environments/bird_sql
   ```

3. Point it at the data with `--env.taskset.data-dir <folder>`, or set `$BIRD_DIR` (dev) / `$BIRD_TRAIN_DIR` (train).

## Run an evaluation

This is a single-turn task, so use the plain `null` harness (no tools) and run it locally:

```bash
vf-run bird-sql -m <model> \
  --client.base-url <OpenAI-compatible URL> \
  --client.api-key-var <ENV_VAR_WITH_KEY> \
  --sampling.temperature 0 \
  --env.agent.harness.id null \
  --env.agent.runtime.type subprocess
```

Without the last two flags, verifiers 0.4.1 defaults to the `bash` coding-agent harness in a Prime cloud sandbox. That adds a shell tool to the prompt and needs a Prime login.

Options:

- `--env.taskset.split dev|train` (default `dev`). Train skips the 377 questions whose gold SQL fails on SQLite 3.35.5 (listed in `bird_sql/train_gold_failures.txt`; ids are positions in `train.json`).
- `--env.taskset.num-tasks N` uses the first N questions.
- `BIRD_SQL_WORKERS` sets how many SQL queries run at once (default: one per CPU core the container may use). A query waits for a free slot before its 30 s timeout starts, so a busy machine queues instead of timing out.

**Serving your own model with vLLM:** start the server with `--generation-config vllm`. By default, `vllm serve` applies the sampling defaults from the model's `generation_config.json`. Qwen2.5 models carry `repetition_penalty: 1.1` there, which silently changes greedy outputs. In our runs it cost about 2 points of accuracy on BIRD dev.

## Scoring details

- Databases are opened read-only, so model SQL cannot modify them.
- Timeouts: 30 s for the model's query, 120 s for the gold query.
- Answer rows are streamed and compared against the gold set, so huge results don't run out of memory.
- Only the first ```` ```sql ```` block is used.
- SQLite version matters for speed. Reference numbers were scored on SQLite 3.35.5. On SQLite 3.49.1 some gold queries were far slower (one went from 0.2 s to over 600 s) and would time out.

## Baselines (BIRD dev, 1,534 questions)

Prompt as in this environment, one greedy answer per question (temperature 0), scored on SQLite 3.35.5.

| Model | Execution accuracy |
| --- | --- |
| GPT-4o-mini (2024-07-18) | 50.5% |
| Qwen2.5-Coder-1.5B-Instruct, zero-shot | 26.5% |
| + SFT (LoRA r16) | 44.4% |
| + GRPO with this reward (LoRA r16) | 47.5% |

Running GRPO and GPT-4o-mini through this environment with `vf-run` gave 47.8% and 50.8%. The answer text was identical on 95% (GRPO via vLLM) and 78% (GPT-4o-mini) of questions, and every identical answer got the same score. The remaining gap is decoding noise.

These numbers use a short, direct prompt and a single sample. Published results on the same model use reasoning-first prompts and self-consistency over many samples, so they are not directly comparable.

## Related environments

Other text-to-SQL environments on the Environments Hub:

- [sql-single-turn](https://app.primeintellect.ai/dashboard/environments/stelioszach/sql-single-turn): single-turn, synthetic templated schemas.
- [skyrl-sql](https://app.primeintellect.ai/dashboard/environments/primeintellect/skyrl-sql): multi-turn, following the SkyRL-SQL protocol, evaluated on Spider.

Both use the legacy verifiers v0 API. This environment uses v1 and BIRD.

## Citation

BIRD: Li et al., *Can LLM Already Serve as a Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs*, NeurIPS 2023.
