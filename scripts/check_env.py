"""Check the verifiers environment scores like the repo's own pipeline on BIRD dev.

1. Gold SQL as the answer -> every question correct (as check_gold.py).
2. Saved model outputs (results/qwen_<name>_dev_raw.jsonl) -> same correct count
   as score_generations.py.
Runs the environment's reward and metrics directly, no model or API calls.
"""
import argparse
import asyncio
import json
import types
from collections import Counter
from pathlib import Path

from bird_sql.taskset import BirdSqlConfig, BirdSqlTaskset

ROOT = Path(__file__).resolve().parents[1]

p = argparse.ArgumentParser()
p.add_argument("--name", default="grpo")  # zeroshot, sft, grpo
args = p.parse_args()

tasks = BirdSqlTaskset(BirdSqlConfig(split="dev")).load()
print(f"loaded {len(tasks)} dev tasks")


async def score(task, text):
    trace = types.SimpleNamespace(last_reply=text)
    reward, error, trivial, gold_error = await asyncio.gather(
        task.execution_match(trace), task.error(trace), task.trivial(trace), task.gold_error(trace))
    return reward, error, trivial, gold_error


async def run(texts):
    sem = asyncio.Semaphore(16)

    async def one(task, text):
        async with sem:
            return await score(task, text)

    return await asyncio.gather(*(one(t, x) for t, x in zip(tasks, texts)))


def report(label, results):
    totals = Counter()
    for reward, error, trivial, gold_error in results:
        totals["correct"] += reward
        totals["error"] += error
        totals["trivial"] += trivial
        totals["gold_error"] += gold_error
    print(f"{label}: " + ", ".join(f"{k} {int(v)}" for k, v in totals.items()))


gold = [f"```sql\n{t.data.gold_sql}\n```" for t in tasks]
report("gold as answer", asyncio.run(run(gold)))

raw = {}
with open(ROOT / "results" / f"qwen_{args.name}_dev_raw.jsonl") as f:
    for line in f:
        r = json.loads(line)
        raw[r["question_id"]] = r["output"]
outputs = [raw[t.data.question_id] for t in tasks]
results = asyncio.run(run(outputs))
report(f"{args.name} outputs", results)

# Per-question comparison with the pipeline's scored file (score_generations.py)
scored = {}
with open(ROOT / "results" / f"qwen_{args.name}_dev.jsonl") as f:
    for line in f:
        r = json.loads(line)
        scored[r["question_id"]] = r["status"] == "correct"
diff = [(t.data.question_id, scored[t.data.question_id], bool(res[0]))
        for t, res in zip(tasks, results) if scored[t.data.question_id] != bool(res[0])]
print(f"disagreements with results/qwen_{args.name}_dev.jsonl: {len(diff)}")
for qid, pipeline, env in diff:
    print(f"  q{qid}: pipeline {'correct' if pipeline else 'wrong'}, env {'correct' if env else 'wrong'}")
