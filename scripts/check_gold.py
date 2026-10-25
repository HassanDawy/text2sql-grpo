# Testing the evaluator
# 1. Load all dev examples.
# 2. For each one, wrap its gold_sql in a ```sql block and call evaluate_one.
# 3. Count how many of each status you get.
# 4. Print the question ID, status, and error for anything that isn’t correct.
# 5.Time the whole run.

import time
from collections import Counter

from data import load_examples, BIRD_DIR
from evaluate import evaluate_one

examples = load_examples(BIRD_DIR / 'dev.json')

counts = Counter()
failures = []
start = time.monotonic()

for i, ex in enumerate(examples):
    fake_output = f"```sql\n{ex['gold_sql']}\n```"
    result = evaluate_one(fake_output, ex)
    counts[result['status']] += 1

    if result["status"] != "correct":
        failures.append((ex["question_id"], result["status"], result['error']))

    if (i + 1) % 100 == 0:
        print(f"{i + 1}/{len(examples)} done")

elapsed = time.monotonic() - start

print()
print(counts)
print(f"Time: {elapsed:.1f} s")

for qid, status, err in failures:
    print(f"q{qid}: {status} | {err}")