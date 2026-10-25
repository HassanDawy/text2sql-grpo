import sys
import time
from collections import Counter
from pathlib import Path

from text2sql.data import load_examples, BIRD_DIR, BIRD_TRAIN_DIR, TRAIN_DB_DIR
from text2sql.evaluate import evaluate_one

ROOT = Path(__file__).resolve().parents[1]

split = sys.argv[1] if len(sys.argv) > 1 else "dev"
if split == "dev":
    examples = load_examples(BIRD_DIR / "dev.json")
elif split == "train":
    examples = load_examples(BIRD_TRAIN_DIR / "train.json", TRAIN_DB_DIR)
else:
    sys.exit(f"Unknown split: {split} (use dev or train)")

counts = Counter()
failures = []
start = time.monotonic()

for i, ex in enumerate(examples):
    fake_output = f"```sql\n{ex['gold_sql']}\n```"
    result = evaluate_one(fake_output, ex)
    counts[result["status"]] += 1
    if result["status"] != "correct":
        failures.append((ex["question_id"], result["status"], result["error"]))
    if (i + 1) % 500 == 0:
        print(f"{i + 1}/{len(examples)} done")

elapsed = time.monotonic() - start
print()
print(counts)
print(f"Time: {elapsed:.1f} s")

out = ROOT / "results" / f"check_gold_{split}_failures.txt"
with open(out, "w") as f:
    for qid, status, err in failures:
        f.write(f"q{qid}: {status} | {err}\n")
print(f"{len(failures)} failures written to {out}")