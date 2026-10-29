import json
from collections import Counter

import argparse

p = argparse.ArgumentParser()
p.add_argument("--name", default="sft")   # zeroshot, sft, grpo
args = p.parse_args()
PATH = f"results/qwen_{args.name}_dev.jsonl"

with open(PATH) as f:
    records = [json.loads(line) for line in f]

errors = [r for r in records if r["status"] == "error"]
print(f"Errors: {len(errors)}")   # should be 718

def error_type(msg):
    return msg.split(": ", 1)[0]  # "no such column: T1.x" -> "no such column"

counts = Counter(error_type(r["error"]) for r in errors)
for msg, n in counts.most_common(15):
    print(f"{n:4}  {msg}")