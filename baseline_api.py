# Baseline models evaluation

from data import load_examples, BIRD_DIR, build_messages
from evaluate import evaluate_one

from dotenv import load_dotenv
from openai import OpenAI

MODEL = "gpt-4o-mini-2024-07-18"
PRICE_IN = 0.15 / 1_000_000
PRICE_OUT = 0.60 / 1_000_000

load_dotenv()
client = OpenAI()

examples = load_examples(BIRD_DIR / 'dev.json')
ex = examples[0]

response = client.chat.completions.create(
    model=MODEL,
    messages=build_messages(ex),
    temperature=0,
)

text = response.choices[0].message.content
usage = response.usage
cost = usage.prompt_tokens * PRICE_IN + usage.completion_tokens * PRICE_OUT

print("=== Model output ===")
print(text)
print()
print("=== Evaluation ===")
print(evaluate_one(text, ex))
print()
print(f"Tokens in: {usage.prompt_tokens}, out: {usage.completion_tokens}")
print(f"Cost: ${cost:.6f}")