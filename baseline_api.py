# Baseline models evaluation

from data import load_examples, BIRD_DIR, build_messages
from evaluate import evaluate_one

from collections import Counter
from pathlib import Path
import json
import time

from dotenv import load_dotenv
from openai import OpenAI, APIError, RateLimitError, APITimeoutError

MODEL = "gpt-4o-mini-2024-07-18"
PRICE_IN = 0.15 / 1_000_000
PRICE_OUT = 0.60 / 1_000_000

HERE = Path(__file__).resolve().parent
OUT_PATH = HERE / 'results' / 'gpt4o_mini_dev.jsonl'

def call_model(client, messages, retries=3):
    #Call API, adding retrying if we get temp failures - increasing wait time on each retry
    for attempt in range(retries):
        try:
            return client.chat.completions.create(
                model=MODEL, messages=messages, temperature=0
            )
        except (RateLimitError, APITimeoutError, APIError) as e:
            wait = 2 ** attempt * 5 #5s, 10s, 20s
            print(f' API error ({type(e).__name__}), retrying in {wait}')
            time.sleep(wait)
        raise RuntimeError("API failed after all retries")

def load_done_ids(path):
    #Question IDs are already saved, so restarting should skip them
    if not path.exists():
        return set()
    with open(path) as f:
        return {json.loads(line)['question_id'] for line in f}

def run():
    load_dotenv()
    client = OpenAI()
    examples = load_examples( BIRD_DIR / 'dev.json')

    OUT_PATH.parent.mkdir(exist_ok=True)
    done = load_done_ids(OUT_PATH)
    todo = [ex for ex in examples if ex['question_id'] not in done]
    print(f'{len(done)} already done, {len(todo)} left')

    with open(OUT_PATH, "a") as f:
        for i, ex in enumerate(todo):
            response = call_model(client, build_messages(ex))
            text = response.choices[0].message.content
            usage = response.usage
            result = evaluate_one(text, ex)

            record = {
                "question_id": ex["question_id"],
                "difficulty": ex["difficulty"],
                "output": text,
                "status": result["status"],
                "reward": result["reward"],
                "error": result["error"],
                "tokens_in": usage.prompt_tokens,
                "tokens_out": usage.completion_tokens,
            }
            f.write(json.dumps(record) + "\n")
            f.flush()

            if (i+1) % 50 == 0:
                print(f'{i+1}/{len(todo)} done')

def summarize():
    with open(OUT_PATH) as f:
        records = [json.loads(line) for line in f]

    scored = [r for r in records if r["status"] != "gold_error"]
    correct = sum(r["status"] == "correct" for r in scored)

    print(f"\nQuestions: {len(records)} ({len(records) - len(scored)} gold_error excluded)")
    print(f"Execution accuracy: {correct / len(scored):.1%}")
    print("Status counts:", Counter(r["status"] for r in records))

    print("\nBy difficulty:")
    for level in ["simple", "moderate", "challenging"]:
        group = [r for r in scored if r["difficulty"] == level]
        acc = sum(r["status"] == "correct" for r in group) / len(group)
        print(f"  {level:12} {acc:.1%}  (n={len(group)})")

    tokens_in = sum(r["tokens_in"] for r in records)
    tokens_out = sum(r["tokens_out"] for r in records)
    cost = tokens_in * PRICE_IN + tokens_out * PRICE_OUT
    print(f"\nTotal cost: ${cost:.4f}  (${cost / len(records) * 1000:.4f} per 1,000 queries)")
    print(f"Avg tokens per query: {tokens_in / len(records):.0f} in, {tokens_out / len(records):.0f} out")


if __name__ == "__main__":
    run()
    summarize()