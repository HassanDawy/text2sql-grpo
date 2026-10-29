"""Count BIRD train examples whose gold answer a trivial query could match.

Categories: empty result, single 0/1 value, single NULL, error/timeout, other.
Read-only, 30 s timeout per query. Python 3.8-compatible.
"""
import json
import os
import sqlite3
import time
from collections import Counter

BIRD = os.environ["BIRD_DIR"]
TRAIN_JSON = os.path.join(BIRD, "train", "train.json")
DB_DIR = os.path.join(BIRD, "train", "train_databases")
OUT = os.path.join("results", "trivial_gold_train.json")
TIMEOUT = 30.0
EXCLUDED_DBS = {"works_cycles"}


def run(sql, db_path):
    conn = sqlite3.connect("file:{}?mode=ro".format(db_path), uri=True)
    deadline = time.time() + TIMEOUT
    conn.set_progress_handler(lambda: 1 if time.time() > deadline else 0, 10000)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def classify(rows):
    if len(rows) == 0:
        return "empty"
    if len(rows) == 1 and len(rows[0]) == 1:
        v = rows[0][0]
        if v is None:
            return "single_null"
        if isinstance(v, (int, float)) and v in (0, 1):
            return "single_01"
    return "other"


def main():
    print("SQLite", sqlite3.sqlite_version)
    with open(TRAIN_JSON) as f:
        examples = json.load(f)
    ids = {"empty": [], "single_01": [], "single_null": [], "error": [], "other": []}
    counts_all, counts_kept = Counter(), Counter()
    start = time.time()
    for i, ex in enumerate(examples):
        db_id = ex["db_id"]
        db_path = os.path.join(DB_DIR, db_id, db_id + ".sqlite")
        try:
            cat = classify(run(ex["SQL"], db_path))
        except Exception:
            cat = "error"
        ids[cat].append(i)
        counts_all[cat] += 1
        if db_id not in EXCLUDED_DBS:
            counts_kept[cat] += 1
        if (i + 1) % 500 == 0:
            print("{}/{} done, {:.0f} min".format(i + 1, len(examples), (time.time() - start) / 60), flush=True)
    print("All train:", dict(counts_all))
    print("Excluding works_cycles:", dict(counts_kept))
    with open(OUT, "w") as f:
        json.dump({"counts_all": counts_all, "counts_kept": counts_kept, "ids": ids}, f)
    print("Wrote", OUT)


if __name__ == "__main__":
    main()