"""
Steps for execution evaluator:

1. Extract the SQL from the model’s text answer ← now
2. Execute a query safely, with a timeout
3. Compare predicted rows against gold rows
4. Score each result, recording why each failure happened
"""
import time
import re
import sqlite3
from data import get_db_path
from pathlib import Path


def extract_sql(text):
    match = re.search(r"```sql\s*(.*?)```", text, re.DOTALL)
    if match is None:
        return None
    return match.group(1).strip()

def execute_sql(db_path, sql, timeout=30.0):
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"   # read-only
    conn = sqlite3.connect(uri, uri=True)

    start = time.monotonic()
    timed_out = False

    def handler():
        nonlocal timed_out
        if time.monotonic() - start > timeout:
            timed_out = True
            return 1          # nonzero = abort the query
        return 0              # zero = keep going

    conn.set_progress_handler(handler, 1000)   # check every 1000 SQLite steps    

    try:
        rows = conn.execute(sql).fetchall()
        return rows, None
    except sqlite3.Error as e:
        if timed_out:
            return None, "timeout"
        return None, str(e)
    finally:
        conn.close()


def rows_match(pred_rows, gold_rows):
    pred, gold = set(pred_rows), set(gold_rows)
    if pred == gold:
        return True
    return False

REWARDS = {
    "correct":    1.0,
    "wrong_rows": 0.1,
    "no_sql":     0.0,
    "error":      0.0,
    "timeout":    0.0,
}

def evaluate_one(model_output, example,timeout=30.0):
    # Extract
    pred_sql = extract_sql(model_output)
    if pred_sql is None:
        status = "no_sql"
        return {"status": status, "reward": REWARDS[status], "error": None}

    # Run gold query first, if breaks -> example broken, not model
    gold_rows, gold_err = execute_sql(example["db_path"], example['gold_sql'], timeout)
    if gold_err is not None:
        return {"status" : 'gold_error', "reward" : None, "error" : gold_err}

    # Run predicted query
    pred_rows, pred_err = execute_sql(example['db_path'], pred_sql, timeout)
    if pred_err is not None:
        if pred_err == 'timeout':
            status = 'timeout'
        else:
            status = 'error'
        return {"status" : status, "reward" : REWARDS[status], "error" : pred_err}

    # Compare
    if rows_match(pred_rows, gold_rows):
        status = "correct"
    else:
        status = "wrong_rows"

    return {"status" : status, "reward" : REWARDS[status], "error" : None}
    

if __name__ == "__main__":
    from data import load_examples, BIRD_DIR 
    examples = load_examples(BIRD_DIR / 'dev.json')
    db = get_db_path("california_schools")
    print(execute_sql(db, "SELECT COUNT(*) FROM schools"))           # rows, None
    print(execute_sql(db, "SELECT * FROM schools WHERE 1 = 0"))      # [], None
    print(execute_sql(db, "SELECT nonsense FROM schools"))           # None, error text
    print(execute_sql(db, "DELETE FROM schools"))                    # None, read-only error
    print(execute_sql(db, "SELECT COUNT(*) FROM schools a, schools b, schools c", timeout=2))
    print(rows_match([("Tripoli",), ("Beirut",)], [("Beirut",), ("Tripoli",)]))              # True
    print(rows_match([("Beirut",), ("Beirut",), ("Tripoli",)], [("Beirut",), ("Tripoli",)])) # True
    print(rows_match([("Beirut",)], [("Beirut",), ("Tripoli",)]))                            # False
    ex = examples[0]
    print(evaluate_one(f"```sql\n{ex['gold_sql']}\n```", ex))   # correct, 1.0
    print(evaluate_one("```sql\nSELECT 'not the answer'\n```", ex))   # wrong_rows, 0.1
    print(evaluate_one("I don't know", ex))                     # no_sql, 0.0