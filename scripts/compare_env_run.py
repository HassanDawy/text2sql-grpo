"""Compare a vf-run eval (traces.jsonl) with the pipeline's scored results, per question.

usage: python compare_env_run.py <run_dir> <pipeline_scored.jsonl> [<pipeline_raw.jsonl>]

For every question where the two disagree, it reports whether the model's answer
text was the same (= a scoring difference) or different (= a generation difference).
"""
import json
import sys
from collections import Counter
from pathlib import Path

run_dir = Path(sys.argv[1])
pipe_path = Path(sys.argv[2])


def last_assistant(obj):
    """Last {'role': 'assistant', 'content': str} found anywhere in obj."""
    found = []

    def walk(x):
        if isinstance(x, dict):
            if x.get("role") == "assistant":
                c = x.get("content")
                if isinstance(c, list):  # content parts: [{"type": "text", "text": ...}]
                    c = "".join(p.get("text", "") for p in c if isinstance(p, dict))
                if isinstance(c, str) and c:
                    found.append(c)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(obj)
    return found[-1] if found else ""


def reward_of(rec):
    r = (rec.get("rewards") or {}).get("execution_match")
    if isinstance(r, dict):
        return float(r.get("score", 0.0))
    return float(r or 0.0)


env = {}
for line in open(run_dir / "traces.jsonl"):
    episode = json.loads(line)
    # Each line is an episode holding a list of traces; use the scored one.
    traces = episode.get("traces") or [episode]
    rec = next((t for t in traces if t.get("rewards")), traces[-1])
    task = rec.get("task") or episode.get("task")
    qid = task["data"]["question_id"]
    reply = rec.get("root_reply")
    if reply is None:
        reply = last_assistant(rec.get("nodes")) or last_assistant(rec.get("calls"))
    env[qid] = {
        "correct": reward_of(rec) == 1.0,
        "error": (rec.get("metrics") or {}).get("error"),
        "text": (reply or "").strip(),
        "timeout": rec.get("is_timeout"),
        "stop": rec.get("stop_condition"),
    }

pipe = {}
for line in open(pipe_path):
    r = json.loads(line)
    pipe[r["question_id"]] = {"status": r["status"], "text": r["output"].strip(),
                              "finish": r.get("finish_reason")}

print(f"env traces: {len(env)}   pipeline rows: {len(pipe)}")
print(f"env correct: {sum(v['correct'] for v in env.values())}   "
      f"env error metric: {sum(1 for v in env.values() if v['error'] == 1.0)}")
print(f"pipeline correct: {sum(v['status'] == 'correct' for v in pipe.values())}")

missing = set(pipe) - set(env)
if missing:
    print(f"missing from env run: {len(missing)} e.g. {sorted(missing)[:10]}")

same_text = sum(1 for q in env if q in pipe and env[q]["text"] == pipe[q]["text"])
print(f"identical answer text: {same_text} / {len(env)}")

kinds = Counter()
examples = {}
for q, e in sorted(env.items()):
    if q not in pipe:
        continue
    p = pipe[q]
    if e["correct"] == (p["status"] == "correct"):
        continue
    kind = ("SCORING (same text)" if e["text"] == p["text"] else "GENERATION (text differs)")
    kind += f": pipeline {p['status']} -> env {'correct' if e['correct'] else 'not correct'}"
    kinds[kind] += 1
    examples.setdefault(kind, []).append(q)

print("\ndisagreements:")
for k, n in kinds.most_common():
    print(f"  {n:4d}  {k}   e.g. {examples[k][:8]}")

# Show one example of each kind in full
for k, qs in examples.items():
    q = qs[0]
    print(f"\n=== q{q}  [{k}]")
    print("--- pipeline output:")
    print(pipe[q]["text"][:600])
    print("--- env output:")
    print(env[q]["text"][:600])
    print(f"--- env stop={env[q]['stop']} timeout={env[q]['timeout']}  pipeline finish={pipe[q]['finish']}")
