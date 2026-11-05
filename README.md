# text2sql-grpo

An open-source RL environment and evaluation harness for text-to-SQL.

This project fine-tunes a small open model (Qwen2.5-Coder-1.5B-Instruct) to translate plain-English questions into SQL, first with supervised fine-tuning (LoRA), then with GRPO using an execution-based reward: the model is rewarded when its query returns the same rows as the correct query.

It uses the same SFT-then-GRPO approach as published text-to-SQL work ([SLM-SQL](https://arxiv.org/abs/2507.22478), [Arctic-Text2SQL-R1](https://huggingface.co/Snowflake/Arctic-Text2SQL-R1-7B)) on a student budget: LoRA, a single consumer GPU, a direct prompt, and one greedy answer per question. It adds:

- **A verifiers v1 environment for BIRD**, published on the Prime Intellect Environments Hub as [hdawy/bird-sql](https://app.primeintellect.ai/dashboard/environments/hdawy/bird-sql): the execution evaluator and binary reward used for GRPO training, with error and trivial-answer metrics for spotting reward hacking. Install with `prime env install hdawy/bird-sql`; details in [its README](environments/bird_sql/README.md).
- **Cost and serving benchmarks** (planned): latency, throughput, and cost per query with vLLM, compared against GPT-4o-mini
- **A held-out e-commerce test set** (planned): ~200 hand-checked questions over a custom schema, never used in training, to test whether gains hold on unfamiliar data

## Evaluation

Execution accuracy on the [BIRD](https://bird-bench.github.io/) dev set (dev_20240627, 1,534 questions), broken down by difficulty. The evaluator runs predicted and gold SQL read-only with a 30 s timeout, compares result sets, and records why each failure happened (no SQL found, SQL error, timeout, or wrong rows). Feeding the gold SQL back through the evaluator scores 1,534/1,534.

All models use the same prompt and greedy decoding (temperature 0).

## Results so far

| Model | BIRD dev EX | Simple | Moderate | Challenging | Cost / 1k queries |
| --- | --- | --- | --- | --- | --- |
| GPT-4o-mini (2024-07-18), zero-shot | 50.5% | 57.9% | 39.9% | 36.6% | $0.17 |
| Qwen2.5-Coder-1.5B-Instruct, zero-shot | 26.5% | 33.2% | 17.2% | 13.1% | pending |
| + SFT (LoRA r16, 8.3k BIRD train examples) | 44.4% | 51.8% | 32.5% | 35.2% | pending |
| + GRPO (execution reward, 8.3k BIRD train questions) | 47.5% | 54.7% | 36.9% | 35.9% | pending |

The zero-shot Qwen model's main failure mode is SQL that doesn't run (47% of answers, vs 5% for GPT-4o-mini), mostly columns referenced through the wrong table. SFT cuts those errors by 73% (718 → 195) and lifts accuracy by 17.9 points, reaching 88% of GPT-4o-mini. Most remaining failures are SQL that runs but returns the wrong rows, which is what GRPO's execution reward targets.

GRPO with an execution-only reward (1 if the rows match, else 0) adds 3.1 points on top of SFT, reaching 94% of GPT-4o-mini. The gain is significant in a paired test (84 questions fixed vs 36 broken, McNemar p ≈ 1e-5), errors drop another 17%, and the share of trivial answers (`SELECT 1`-style) stays flat throughout training, so the gain doesn't come from gaming the reward. Most of it arrives in the first ~400 of 1,035 steps; after that the model's outputs become nearly deterministic, and most groups of sampled answers stop carrying a learning signal.

Most of the gain comes from queries that already ran but returned the wrong rows (59 fixed), plus 25 fixed errors. 36 previously correct answers broke, mostly into wrong rows; checked by hand, about 9 of those are benchmark issues, ambiguous questions or SFT luck, and most of the rest are schema-grounding mistakes (wrong table, join or column). That is also the model's main remaining weakness: 113 of its 161 errors reference a real column through the wrong table.

The challenging split is small (145 questions, about ±8 points), so its numbers are noisy.

These numbers are not directly comparable with SLM-SQL, which reports 61.95% for the same base model after SFT + RL, using reasoning-first prompts and self-consistency over 16–64 samples. This project uses a direct prompt and a single greedy answer.

## Reproducing with the environment

Running the GRPO model (served with vLLM) and GPT-4o-mini through the published environment with `vf-run` gives 47.8% and 50.8%, against 47.5% and 50.5% from this repo's own pipeline. The answer text is identical on 95% (GRPO) and 78% (GPT-4o-mini) of questions, and every identical answer gets the same score, so the remaining gap is decoding noise (`scripts/compare_env_run.py` does the per-question comparison). The command is in the [environment README](environments/bird_sql/README.md).

One pitfall: `vllm serve` applies the sampling defaults in a model's `generation_config.json` unless started with `--generation-config vllm`. The merged models inherit Qwen's `repetition_penalty: 1.1`, which dropped the GRPO model to 45.5% even at temperature 0.

## Related environments

Existing text-to-SQL environments on the Prime Intellect Environments Hub include [sql-single-turn](https://app.primeintellect.ai/dashboard/environments/stelioszach/sql-single-turn) (synthetic schemas) and [skyrl-sql](https://app.primeintellect.ai/dashboard/environments/primeintellect/skyrl-sql) (multi-turn, Spider). Both target the legacy verifiers v0 API; this project targets v1 and BIRD.

## References

- **BIRD:** Li et al., *Can LLM Already Serve as a Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs*, NeurIPS 2023.
- **SLM-SQL** and **Arctic-Text2SQL-R1:** the GRPO text-to-SQL results this project reproduces (linked above).
- **Qwen2.5-Coder:** Qwen team, Alibaba (the base model).
- **vLLM:** Kwon et al., *Efficient Memory Management for Large Language Model Serving with PagedAttention*, SOSP 2023.
- **TRL:** Hugging Face's library for SFT and GRPO training.
- **verifiers:** Brown, *Verifiers: Environments for LLM Reinforcement Learning*, Prime Intellect, 2025.

**Status:** SFT, GRPO and the environment are done. Cost/serving benchmarks and the e-commerce test set are next.