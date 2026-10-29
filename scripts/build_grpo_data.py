"""Build GRPO data from the SFT split, so train/val are identical by construction.

Each row: question_id, db_id, prompt (system + user messages), gold_sql.
TRL passes db_id and gold_sql to text2sql/reward.py as keyword arguments.
"""
import json
from pathlib import Path

from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
SFT_DIR = Path("/workspace/sft_data")
OUT_DIR = Path("/workspace/grpo_data")
MODEL = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
MAX_PROMPT = 3072

# Gold queries that errored in count_trivial_gold but passed check_gold
# (likely near the 30 s timeout). A failing gold query makes reward.py raise.
trivial = json.loads((ROOT / "results" / "trivial_gold_train.json").read_text())
SLOW_GOLD = set(trivial["ids"]["error"])
TRIVIAL = set(trivial["ids"]["empty"] + trivial["ids"]["single_01"] + trivial["ids"]["single_null"])

tok = AutoTokenizer.from_pretrained(MODEL)
OUT_DIR.mkdir(parents=True, exist_ok=True)

for split in ["train", "val"]:
    rows = [json.loads(line) for line in open(SFT_DIR / f"{split}.jsonl")]
    out, dropped = [], []
    for r in rows:
        if r["question_id"] in SLOW_GOLD:
            dropped.append(r["question_id"])
            continue
        answer = r["completion"][0]["content"]
        assert answer.startswith("```sql\n") and answer.endswith("\n```"), r["question_id"]
        out.append({
            "question_id": r["question_id"],
            "db_id": r["db_id"],
            "prompt": r["prompt"],
            "gold_sql": answer[len("```sql\n"):-len("\n```")],
        })

    lengths = [len(tok(tok.apply_chat_template(r["prompt"], tokenize=False,
                                               add_generation_prompt=True))["input_ids"])
               for r in out]
    n_trivial = sum(r["question_id"] in TRIVIAL for r in out)

    with open(OUT_DIR / f"{split}.jsonl", "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")

    print(f"{split}: {len(out)} rows (dropped slow gold: {sorted(dropped)}) | "
          f"trivial gold: {n_trivial} ({n_trivial / len(out):.1%}) | "
          f"prompt tokens max {max(lengths)}, over {MAX_PROMPT}: {sum(x > MAX_PROMPT for x in lengths)}")