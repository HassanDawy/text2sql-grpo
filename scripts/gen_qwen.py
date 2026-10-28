import argparse
import json
from pathlib import Path

from vllm import LLM, SamplingParams

from text2sql.data import BIRD_DIR, load_examples, build_messages

ROOT = Path(__file__).resolve().parents[1]

p = argparse.ArgumentParser()
p.add_argument("--model", default="Qwen/Qwen2.5-Coder-1.5B-Instruct")
p.add_argument("--name", default="zeroshot")      # -> results/qwen_<name>_dev_raw.jsonl
p.add_argument("--limit", type=int, default=None)  # e.g. 5 for a quick test
args = p.parse_args()

OUT_PATH = ROOT / "results" / f"qwen_{args.name}_dev_raw.jsonl"

examples = load_examples(BIRD_DIR / "dev.json")
if args.limit:
    examples = examples[: args.limit]
conversations = [build_messages(ex) for ex in examples]

# Same settings as the zero-shot baseline
llm = LLM(model=args.model, dtype="bfloat16", max_model_len=16384)
params = SamplingParams(temperature=0, max_tokens=512)

outputs = llm.chat(conversations, params)

OUT_PATH.parent.mkdir(exist_ok=True)
with open(OUT_PATH, "w") as f:
    for ex, out in zip(examples, outputs):
        gen = out.outputs[0]
        f.write(json.dumps({
            "question_id": ex["question_id"],
            "difficulty": ex["difficulty"],
            "output": gen.text,
            "finish_reason": gen.finish_reason,
            "tokens_in": len(out.prompt_token_ids),
            "tokens_out": len(gen.token_ids),
        }) + "\n")
print(f"Wrote {len(outputs)} outputs to {OUT_PATH}")