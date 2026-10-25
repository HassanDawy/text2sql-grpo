import json
from collections import Counter
from pathlib import Path

from text2sql.data import load_examples, BIRD_DIR
from text2sql.evaluate import evaluate_one

HERE = Path(__file__).resolve().parent
RAW_PATH = HERE / "results" / "qwen_zeroshot_dev_raw.jsonl"
SCORED_PATH = HERE / "results" / "qwen_zeroshot_dev.jsonl"

examples = load_examples(BIRD_DIR / "dev.json")
by_id = {ex["question_id"]: ex for ex in examples}

with open(RAW_PATH) as f:
    raw = [json.loads(line) for line in f]

records = []
for i,r in enumerate(raw):
    result = evaluate_one(r['output'], by_id[r['question_id']])
    records.append({**r, **result})
    if (i+1) % 100 == 0:
        print(f'{i+1}/{len(raw)} scored')

with open(SCORED_PATH, 'w') as f:
    for rec in records:
        f.write(json.dumps(rec) + '\n')

scored = [r for r in records if r['status'] != 'gold_error']
correct = sum(r['status'] == 'correct' for r in scored)

print(f"\nQuestions: {len(records)} ({len(records) - len(scored)} gold_error excluded)")
print(f"Execution accuracy: {correct / len(scored):.1%}")
print("Status counts:", Counter(r["status"] for r in records))

print("\nBy difficulty:")
for level in ["simple", "moderate", "challenging"]:
    group = [r for r in scored if r["difficulty"] == level]
    acc = sum(r["status"] == "correct" for r in group) / len(group)
    print(f"  {level:12} {acc:.1%}  (n={len(group)})")

hit_cap = [r for r in records if r["finish_reason"] == "length"]
print(f"\nHit token cap: {len(hit_cap)}; their statuses:", Counter(r["status"] for r in hit_cap))