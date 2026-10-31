"""Merge a LoRA adapter into a base model so vLLM can load it as a normal model."""
import argparse

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

p = argparse.ArgumentParser()
p.add_argument("--base", default="Qwen/Qwen2.5-Coder-1.5B-Instruct")
p.add_argument("--adapter", default="/workspace/checkpoints/sft_lora_r16/final")
p.add_argument("--out", default="/workspace/models/sft_lora_r16_merged")
args = p.parse_args()

model = AutoModelForCausalLM.from_pretrained(args.base, dtype=torch.bfloat16)
model = PeftModel.from_pretrained(model, args.adapter).merge_and_unload()
model.save_pretrained(args.out)
AutoTokenizer.from_pretrained(args.base).save_pretrained(args.out)
print(f"Saved merged model to {args.out}")