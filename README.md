# text2sql-grpo

An open-source RL environment and evaluation harness for text-to-SQL.

This project fine-tunes a small open model (Qwen2.5-Coder-1.5B-Instruct) to translate plain-English questions into SQL, first with supervised fine-tuning (LoRA), then with GRPO using an execution-based reward: the model is rewarded when its query returns the same rows as the correct query.

It reproduces and extends published GRPO text-to-SQL results ([SLM-SQL](https://arxiv.org/abs/2507.22478), [Arctic-Text2SQL-R1](https://huggingface.co/Snowflake/Arctic-Text2SQL-R1-7B)) on a student budget, and adds:

- **Cost and serving benchmarks:** latency, throughput, and cost per query with vLLM, compared against GPT-4o-mini
- **A held-out e-commerce test set:** ~200 hand-checked questions over a custom schema, never used in training, to test whether gains hold on unfamiliar data
- **A reusable RL environment:** the execution evaluator and reward packaged so others can run them directly

**Evaluation:** execution accuracy on the [BIRD](https://bird-bench.github.io/) dev set (broken down by difficulty) and on the e-commerce test set, across three stages: zero-shot baseline, SFT, and GRPO.

**Status:** in progress. Results will be added as each stage completes.