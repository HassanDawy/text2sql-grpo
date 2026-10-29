"""LoRA GRPO on top of the merged SFT model (see NOTES section 8)."""
import argparse
import json
import os
import time

import torch
from datasets import load_dataset
from dotenv import load_dotenv
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import GRPOConfig, GRPOTrainer

from text2sql.reward import execution_reward, error_rate, trivial_rate

MODEL = "/workspace/models/sft_lora_r16_merged"   # start (and KL reference) = SFT model
DATA_DIR = "/workspace/grpo_data"
OUT_DIR = "/workspace/checkpoints/grpo_lora_r16"

parser = argparse.ArgumentParser()
parser.add_argument("--smoke", action="store_true",
                    help="10 steps on the longest prompts, 1 eval on 20 val questions, no W&B")
args = parser.parse_args()

load_dotenv()
os.environ.setdefault("WANDB_PROJECT", "text2sql-grpo")

# 1. Data: prompt (system + user), plus db_id and gold_sql for the reward
data = load_dataset("json", data_files={
    "train": f"{DATA_DIR}/train.jsonl",
    "val": f"{DATA_DIR}/val.jsonl",
})
train, val = data["train"], data["val"]

if args.smoke:
    # Longest prompts first, to test peak GPU memory
    lengths = [len(json.dumps(p)) for p in train["prompt"]]
    longest = sorted(range(len(train)), key=lambda i: -lengths[i])[:80]
    train = train.select(longest)
    val = val.select(range(20))

# 2. Model and a fresh LoRA adapter. With beta > 0, the reference model is
#    this same model with the adapter switched off, i.e. exactly the SFT model.
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.bfloat16)

lora = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules="all-linear",
    task_type="CAUSAL_LM",
)

# 3. GRPO settings
config = GRPOConfig(
    output_dir=OUT_DIR + ("_smoke" if args.smoke else ""),
    num_train_epochs=1,
    max_steps=10 if args.smoke else -1,
    # 2 x 24 = 48 answers per optimizer step = 8 questions x 6 answers
    per_device_train_batch_size=2,
    gradient_accumulation_steps=24,
    generation_batch_size=12,            # generate 2 questions x 6 answers at a time (OOM at 48)
    num_generations=6,
    temperature=1.0,
    max_completion_length=512,
    learning_rate=1e-5,
    lr_scheduler_type="cosine",
    warmup_steps=20,
    beta=0.04,
    num_iterations=1,
    loss_type="dapo",                    # TRL default; no length bias
    reward_weights=[1.0, 0.0, 0.0],      # error_rate and trivial_rate only monitor
    bf16=True,
    gradient_checkpointing=True,
    # Eval on the 300 val questions (never BIRD dev), 2 answers each
    eval_strategy="steps",
    eval_steps=5 if args.smoke else 100,
    num_generations_eval=2,
    per_device_eval_batch_size=8,
    logging_steps=1 if args.smoke else 5,
    log_completions=True,
    save_strategy="no" if args.smoke else "steps",
    save_steps=100,
    save_total_limit=3,
    report_to="none" if args.smoke else "wandb",
    run_name="grpo-lora-r16-beta0.04",
    seed=0,
)

trainer = GRPOTrainer(
    model=model,
    reward_funcs=[execution_reward, error_rate, trivial_rate],
    args=config,
    train_dataset=train,
    eval_dataset=val,
    processing_class=tok,
    peft_config=lora,
)
trainer.model.print_trainable_parameters()

# 4. Train
start = time.monotonic()
trainer.train()
elapsed = time.monotonic() - start

if args.smoke:
    print(f"total {elapsed / 60:.1f} min for 10 steps + 2 evals on 20 val questions")
    print(f"peak GPU memory: {torch.cuda.max_memory_allocated() / 1e9:.1f} GB")
else:
    trainer.save_model(f"{OUT_DIR}/final")
    print(f"done in {elapsed / 3600:.1f} h")