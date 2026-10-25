import json
from pathlib import Path

from vllm import LLM, SamplingParams

from data import BIRD_DIR, load_examples, build_messages

MODEL = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
HERE = Path(__file__).resolve().parent
OUT_PATH = HERE / "results" / "qwen_zeroshot_dev_raw.jsonl"

examples = load_examples(BIRD_DIR / 'dev.json')
conversations = [build_messages(ex) for ex in examples]

llm = LLM(model=MODEL, dtype = 'bfloat16', max_model_len=16384)
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
            'finish_reason': gen.finish_reason,
            "tokens_in": len(out.prompt_token_ids),
            "tokens_out": len(gen.tokens_id),
        }) + "\n")
print(f'Wrote {len(outputs)} outputs to {OUT_PATH}')