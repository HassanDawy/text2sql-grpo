import json
from pathlib import Path
import sqlite3

HERE = Path(__file__).resolve().parent
BIRD_DIR = HERE / "../../dev/dev_20240627"
DB_DIR = BIRD_DIR / "dev_databases/dev_databases"

def get_db_path(db_id):
    return DB_DIR / db_id / f"{db_id}.sqlite"

def get_schema(db_path):
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT sql FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    conn.close()
    return '\n\n'.join(row[0] for row in rows)

def load_examples(json_path):
    with open(json_path) as f:
        data = json.load(f)

    schema_cache = {} #To ensure each database is read once
    examples = []

    for ex in data:
        db_id = ex["db_id"]
        db_path = get_db_path(db_id)

        if db_id not in schema_cache:
            schema_cache[db_id] = get_schema(db_path)

        examples.append({
            "question":   ex["question"],
            "evidence":   ex["evidence"],
            "gold_sql":   ex["SQL"],
            "difficulty": ex.get("difficulty"),   # None for train, which has no difficulty
            "db_path":    db_path,
            "schema":     schema_cache[db_id],
        })

    return examples

if __name__ == "__main__":
    examples = load_examples(BIRD_DIR / "dev.json")
    print(len(examples))                
    print(examples[0]["question"])
    print(examples[0]["schema"][:300])