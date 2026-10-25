import json
from pathlib import Path
import sqlite3
import os

HERE = Path(__file__).resolve().parent
BIRD_DIR = Path(os.environ.get("BIRD_DIR", HERE / "../../../dev/dev_20240627"))
DB_DIR = BIRD_DIR / "dev_databases/dev_databases"

BIRD_TRAIN_DIR = Path(os.environ.get("BIRD_TRAIN_DIR", BIRD_DIR / "../train"))
TRAIN_DB_DIR = BIRD_TRAIN_DIR / "train_databases/train_databases"


def get_db_path(db_id, db_dir=DB_DIR):
    return db_dir / db_id / f"{db_id}.sqlite"


def get_schema(db_path):
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"   # read-only
    conn = sqlite3.connect(uri, uri=True)
    rows = conn.execute(
        "SELECT sql FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    conn.close()
    return '\n\n'.join(row[0] for row in rows)


def load_examples(json_path, db_dir=DB_DIR):
    with open(json_path) as f:
        data = json.load(f)

    schema_cache = {}  # To ensure each database is read once
    examples = []

    for i, ex in enumerate(data):
        db_id = ex["db_id"]
        db_path = get_db_path(db_id, db_dir)

        if db_id not in schema_cache:
            schema_cache[db_id] = get_schema(db_path)

        examples.append({
            "question_id": ex.get("question_id", i),  # train has no ids: use position
            "question":   ex["question"],
            "evidence":   ex["evidence"],
            "gold_sql":   ex["SQL"],
            "difficulty": ex.get("difficulty"),       # None for train
            "db_path":    db_path,
            "schema":     schema_cache[db_id],
        })

    return examples


# If scaled this can be moved to its own file
SYSTEM_PROMPT = (
    "You are an expert in SQLite. Given a database schema, an optional hint, "
    "and a question, write exactly one SQLite query that answers the question, "
    "using only the tables and columns in the schema. "
    "Return the query in a ```sql code block."
)


def build_messages(example):
    evidence = example["evidence"] or "None"

    user_content = (
        f"### Database schema:\n{example['schema']}\n\n"
        f"### Hint:\n{evidence}\n\n"
        f"### Question:\n{example['question']}"
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_content},
    ]


if __name__ == "__main__":
    examples = load_examples(BIRD_DIR / "dev.json")
    msgs = build_messages(examples[0])
    print(msgs[1]["content"])