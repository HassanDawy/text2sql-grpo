"""Questions SFT got right and GRPO got wrong, written to markdown for labeling by hand.

Writes analysis/grpo_broken.md (36 questions on BIRD dev). Refuses to overwrite it,
so your labels are safe; pass --force to regenerate.
"""
import argparse
import json
from pathlib import Path

from text2sql.data import load_examples, BIRD_DIR
from text2sql.evaluate import extract_sql

p = argparse.ArgumentParser()
p.add_argument("--force", action="store_true")
args = p.parse_args()

OUT = Path("analysis/grpo_broken.md")
if OUT.exists() and not args.force:
    raise SystemExit(f"{OUT} exists (may hold your labels); use --force to overwrite")


def load(name):
    with open(f"results/qwen_{name}_dev.jsonl") as f:
        return {r["question_id"]: r for r in map(json.loads, f)}


sft, grpo = load("sft"), load("grpo")
examples = {ex["question_id"]: ex for ex in load_examples(BIRD_DIR / "dev.json")}

broken = sorted(q for q in sft
                if sft[q]["status"] == "correct" and grpo[q]["status"] != "correct")

with open(OUT, "w", encoding="utf-8") as f:
    f.write(f"# SFT correct -> GRPO wrong ({len(broken)} questions, BIRD dev)\n\n")
    for i, q in enumerate(broken, 1):
        ex, g = examples[q], grpo[q]
        status = g["status"]
        if status == "error" and g.get("error"):
            status += f" ({g['error']})"
        f.write(f"## {i}. q{q} ({ex['difficulty']}, {ex['db_path'].stem}) -> GRPO {status}\n\n")
        f.write(f"**Question:** {ex['question']}\n\n")
        f.write(f"**Hint:** {ex['evidence'] or 'None'}\n\n")
        f.write(f"**SFT (correct):**\n```sql\n{extract_sql(sft[q]['output'])}\n```\n\n")
        f.write(f"**GRPO:**\n```sql\n{extract_sql(g['output'])}\n```\n\n")
        f.write(f"**Gold:**\n```sql\n{ex['gold_sql']}\n```\n\n")
        f.write("**Pattern:** \n\n---\n\n")
print(f"Wrote {len(broken)} questions to {OUT}")
