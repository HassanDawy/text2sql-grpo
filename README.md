# text2sql-grpo

An open-source RL environment and evaluation harness for text-to-SQL.

This project fine-tunes a small open model (Qwen2.5-Coder-1.5B-Instruct) to translate plain-English questions into SQL, first with supervised fine-tuning (LoRA), then with GRPO using an execution-based reward: the model is rewarded when its query returns the same rows as the correct query.

It reproduces and extends published GRPO text-to-SQL results ([SLM-SQL](https://arxiv.org/abs/2507.22478), [Arctic-Text2SQL-R1](https://huggingface.co/Snowflake/Arctic-Text2SQL-R1-7B)) on a student budget, and adds:

- **Cost and serving benchmarks:** latency, throughput, and cost per query with vLLM, compared against GPT-4o-mini
- **A held-out e-commerce test set:** ~200 hand-checked questions over a custom schema, never used in training, to test whether gains hold on unfamiliar data
- **A verifiers v1 environment for BIRD:** the execution evaluator and reward packaged for Prime Intellect's verifiers library (in progress)

## Evaluation

Execution accuracy on the [BIRD](https://bird-bench.github.io/) dev set (dev_20240627, 1,534 questions), broken down by difficulty, plus the e-commerce test set. The evaluator runs predicted and gold SQL read-only with a 30 s timeout, compares result sets, and records why each failure happened (no SQL found, SQL error, timeout, or wrong rows). Feeding the gold SQL back through the evaluator scores 1,534/1,534.

All models use the same prompt and greedy decoding (temperature 0).

## Results so far

| Model | BIRD dev EX | Simple | Moderate | Challenging | Cost / 1k queries |
| --- | --- | --- | --- | --- | --- |
| GPT-4o-mini (2024-07-18), zero-shot | 50.5% | 57.9% | 39.9% | 36.6% | $0.17 |
| Qwen2.5-Coder-1.5B-Instruct, zero-shot | 26.5% | 33.2% | 17.2% | 13.1% | pending |
| + SFT (LoRA r16, 8.3k BIRD train examples) | 44.4% | 51.8% | 32.5% | 35.2% | pending |
| + GRPO | — | | | | |

The zero-shot Qwen model's main failure mode is SQL that doesn't run (47% of answers, vs 5% for GPT-4o-mini), mostly columns referenced through the wrong table. SFT cuts those errors by 73% (718 → 195) and lifts accuracy by 17.9 points, reaching 88% of GPT-4o-mini. Most remaining failures are SQL that runs but returns the wrong rows, which is what GRPO's execution reward targets.

The challenging split is small (145 questions, about ±8 points), so its numbers are noisy.

## Related environments

Existing text-to-SQL environments on the Prime Intellect Environments Hub include [sql-single-turn](https://app.primeintellect.ai/dashboard/environments/stelioszach/sql-single-turn) (synthetic schemas) and [skyrl-sql](https://app.primeintellect.ai/dashboard/environments/primeintellect/skyrl-sql) (multi-turn, Spider). Both target the legacy verifiers v0 API; this project targets v1 and BIRD.

## References

- **BIRD:** Li et al., *Can LLM Already Serve as a Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs*, NeurIPS 2023.
- **SLM-SQL** and **Arctic-Text2SQL-R1:** the GRPO text-to-SQL results this project reproduces (linked above).
- **Qwen2.5-Coder:** Qwen team, Alibaba (the base model).
- **vLLM:** Kwon et al., *Efficient Memory Management for Large Language Model Serving with PagedAttention*, SOSP 2023.
- **TRL:** Hugging Face's library for SFT and GRPO training.
- **verifiers:** Brown, *Verifiers: Environments for LLM Reinforcement Learning*, Prime Intellect, 2025.

**Status:** in progress. Results are added as each stage completes.