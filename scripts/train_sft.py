"""LoRA SFT of Qwen2.5-Coder-1.5B-Instruct on BIRD train (see NOTES section 7)."""
import argparse
import json
import os

import torch
from datasets import load_dataset
from dotenv import load_dotenv
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer

MODEL = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
DATA_DIR = "/workspace/sft_data"
OUT_DIR = "/workspace/checkpoints/sft_lora_r16"

parser = argparse.ArgumentParser()
parser.add_argument("--smoke", action="store_true",
                    help="5 steps on the longest examples, no W&B")
args = parser.parse_args()

load_dotenv()
os.environ.setdefault("WANDB_PROJECT", "text2sql-grpo")

# 1. Data: prompt (system + user) and completion (assistant gold SQL)
data = load_dataset("json", data_files={
    "train": f"{DATA_DIR}/train.jsonl",
    "val": f"{DATA_DIR}/val.jsonl",
})
data = data.remove_columns(["question_id", "db_id"])
train, val = data["train"], data["val"]

if args.smoke:
    # Longest examples first, to test peak GPU memory
    lengths = [len(json.dumps(p)) for p in train["prompt"]]
    longest = sorted(range(len(train)), key=lambda i: -lengths[i])[:40]
    train = train.select(longest)
    val = val.select(range(20))

# 2. Model and LoRA
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.bfloat16)

lora = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules="all-linear",
    task_type="CAUSAL_LM",
)

# 3. Training settings
config = SFTConfig(
    output_dir=OUT_DIR + ("_smoke" if args.smoke else ""),
    num_train_epochs=2,
    max_steps=5 if args.smoke else -1,
    per_device_train_batch_size=2,
    per_device_eval_batch_size=2,
    gradient_accumulation_steps=8,      # 2 x 8 = 16 effective
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_steps=30,
    bf16=True,
    gradient_checkpointing=True,
    max_length=4096,
    completion_only_loss=True,          # loss on the SQL answer only
    packing=False,
    logging_steps=1 if args.smoke else 10,
    eval_strategy="steps",
    eval_steps=5 if args.smoke else 100,
    save_strategy="no" if args.smoke else "steps",
    save_steps=100,
    save_total_limit=3,
    report_to="none" if args.smoke else "wandb",
    run_name="sft-lora-r16",
    seed=0,
)

trainer = SFTTrainer(
    model=model,
    args=config,
    train_dataset=train,
    eval_dataset=val,
    processing_class=tok,
    peft_config=lora,
)

# 4. Sanity checks before training
ex = trainer.train_dataset[0]
answer_tokens = sum(ex["completion_mask"]) if "completion_mask" in ex else None
print(f"example 0: {len(ex['input_ids'])} tokens, {answer_tokens} with loss")
trainer.model.print_trainable_parameters()

# 5. Train
trainer.train()

if args.smoke:
    print(f"peak GPU memory: {torch.cuda.max_memory_allocated() / 1e9:.1f} GB")
else:
    trainer.save_model(f"{OUT_DIR}/final")