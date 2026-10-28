"""Build SFT data from BIRD train (minus gold_error) and measure token lengths."""
import json
import random
from pathlib import Path

from transformers import AutoTokenizer

from bird_sql.taskset import load_failed_ids
from text2sql.data import load_examples, build_messages, BIRD_TRAIN_DIR, TRAIN_DB_DIR

OUT_DIR = Path("/workspace/sft_data")
MODEL = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
VAL_SIZE = 300
SEED = 0

# 1. Load train and drop the broken examples (377)
examples = load_examples(BIRD_TRAIN_DIR / "train.json", TRAIN_DB_DIR)
failed = load_failed_ids("train")
examples = [ex for ex in examples if ex["question_id"] not in failed]
assert len(examples) == 9051, len(examples)

# 2. Prompt v1 + gold SQL as the assistant answer
rows = [
    {
        "question_id": ex["question_id"],
        "db_id": Path(ex["db_path"]).stem,
        "prompt": build_messages(ex),
        "completion": [{"role": "assistant",
                        "content": f"```sql\n{ex['gold_sql'].strip()}\n```"}],
    }
    for ex in examples
]

# 3. Random train/validation split (validation is for overfitting checks only)
random.Random(SEED).shuffle(rows)
val, train = rows[:VAL_SIZE], rows[VAL_SIZE:]

OUT_DIR.mkdir(parents=True, exist_ok=True)
for name, split in [("train", train), ("val", val)]:
    with open(OUT_DIR / f"{name}.jsonl", "w") as f:
        for r in split:
            f.write(json.dumps(r) + "\n")
print(f"train: {len(train)}  val: {len(val)}  -> {OUT_DIR}")

# 4. Token length of each full conversation (prompt + answer)
tok = AutoTokenizer.from_pretrained(MODEL)
lengths = sorted(
    len(tok(tok.apply_chat_template(r["prompt"] + r["completion"], tokenize=False))["input_ids"])
    for r in rows
)
n = len(lengths)
print(f"tokens: mean {sum(lengths) / n:.0f} | p95 {lengths[int(n * 0.95)]} "
      f"| p99 {lengths[int(n * 0.99)]} | max {lengths[-1]}")
for cap in [2048, 3072, 4096]:
    print(f"  over {cap}: {sum(x > cap for x in lengths)}")