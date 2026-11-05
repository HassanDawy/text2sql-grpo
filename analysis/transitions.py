"""Per-question status transitions between two runs (default: SFT -> GRPO) on BIRD dev.

Rows = status in the first run, columns = status in the second run.
Off-diagonal cells are where the second run changed something.
"""
import argparse
import json
from collections import Counter

p = argparse.ArgumentParser()
p.add_argument("--before", default="sft")   # zeroshot, sft, grpo
p.add_argument("--after", default="grpo")
args = p.parse_args()


def load(name):
    with open(f"results/qwen_{name}_dev.jsonl") as f:
        return {r["question_id"]: r["status"] for r in map(json.loads, f)}


before, after = load(args.before), load(args.after)
assert before.keys() == after.keys(), "runs cover different questions"

pairs = Counter((before[q], after[q]) for q in before)
statuses = ["correct", "wrong_rows", "error"]

print(f"{args.before} (rows) -> {args.after} (columns), {len(before)} questions\n")
print(f"{'':12}" + "".join(f"{s:>12}" for s in statuses) + f"{'total':>8}")
for b in statuses:
    row = [pairs[(b, a)] for a in statuses]
    print(f"{b:12}" + "".join(f"{n:12}" for n in row) + f"{sum(row):8}")
print(f"{'total':12}" + "".join(f"{sum(pairs[(b, a)] for b in statuses):12}" for a in statuses))

fixed = sum(pairs[(b, "correct")] for b in statuses if b != "correct")
broken = sum(pairs[("correct", a)] for a in statuses if a != "correct")
print(f"\nfixed {fixed}, broken {broken}, net {fixed - broken:+d}")

other = {k: v for k, v in pairs.items() if k[0] not in statuses or k[1] not in statuses}
if other:
    print(f"other statuses (not in table): {other}")
