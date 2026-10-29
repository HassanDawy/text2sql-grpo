import json
import random

from text2sql.data import load_examples, BIRD_DIR
from text2sql.evaluate import extract_sql

import argparse

p = argparse.ArgumentParser()
p.add_argument("--name", default="sft")   # zeroshot, sft, grpo
args = p.parse_args()
PATH = f"results/qwen_{args.name}_dev.jsonl"
OUT = f"analysis/{args.name}_failures.md"

with open(PATH) as f:
    records = [json.loads(line) for line in f]
examples = {ex["question_id"]: ex for ex in load_examples(BIRD_DIR / "dev.json")}

wrong = [r for r in records if r["status"] == "wrong_rows"]
sample = random.Random(0).sample(wrong, 20)   # fixed seed: same 20 every time

with open(OUT, "w", encoding="utf-8") as f:
    for i, r in enumerate(sample, 1):
        ex = examples[r["question_id"]]
        f.write(f"## {i}. q{r['question_id']} ({ex['difficulty']}, {ex['db_path'].stem})\n\n")
        f.write(f"**Question:** {ex['question']}\n\n")
        f.write(f"**Hint:** {ex['evidence'] or 'None'}\n\n")
        f.write(f"**Predicted:**\n```sql\n{extract_sql(r['output'])}\n```\n\n")
        f.write(f"**Gold:**\n```sql\n{ex['gold_sql']}\n```\n\n")
        f.write("**Pattern:** \n\n---\n\n")
print(f"Wrote {len(sample)} failures to {OUT}")