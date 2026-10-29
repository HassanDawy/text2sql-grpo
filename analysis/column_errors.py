import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

from text2sql.data import load_examples, BIRD_DIR

import argparse

p = argparse.ArgumentParser()
p.add_argument("--name", default="sft")   # zeroshot, sft, grpo
args = p.parse_args()
PATH = f"results/qwen_{args.name}_dev.jsonl"

# 1. Load scored results and the examples (for db_path)
with open(PATH) as f:
    records = [json.loads(line) for line in f]
examples = {ex["question_id"]: ex for ex in load_examples(BIRD_DIR / "dev.json")}

col_errors = [r for r in records
              if r["status"] == "error" and r["error"].startswith("no such column")]
print(f"no such column errors: {len(col_errors)}")   # should be 621

# 2. Get every column name in a database (cached, since many questions share a db)
column_cache = {}

def get_columns(db_path):
    if db_path not in column_cache:
        uri = Path(db_path).resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
        cols = []
        for t in tables:
            # row[1] is the column name in PRAGMA table_info output
            cols += [row[1] for row in conn.execute(f'PRAGMA table_info("{t}")')]
        conn.close()
        column_cache[db_path] = cols
    return column_cache[db_path]

# 3. Classify each error
def norm(s):
    # keep only letters and digits: "FRPM Count (K-12)" -> "frpmcountk12"
    return re.sub(r"[^a-z0-9]", "", s.lower())

def classify(name, columns):
    lower_cols = [c.lower() for c in columns]
    if name.lower() in lower_cols:
        return "wrong_table"
    if any(" " in c and c.split()[0] == name.lower() for c in lower_cols):
        return "missing_quotes"
    n = norm(name)
    if n and any(norm(c).startswith(n) for c in columns):
        return "mangled_name"
    return "made_up"

counts = Counter()
samples = {"wrong_table": [], "missing_quotes": [], "mangled_name": [], "made_up": []}

for r in col_errors:
    raw = r["error"].split(": ", 1)[1]           # "T1.Free"
    name = raw.split(".")[-1].strip('`"[]')      # "Free"
    ex = examples[r["question_id"]]
    kind = classify(name, get_columns(ex["db_path"]))
    counts[kind] += 1
    if len(samples[kind]) < 5:
        samples[kind].append((r["question_id"], raw))

# 4. Report
print(counts)
for kind, items in samples.items():
    print(f"\n{kind}:")
    for qid, raw in items:
        print(f"  q{qid}: {raw}")