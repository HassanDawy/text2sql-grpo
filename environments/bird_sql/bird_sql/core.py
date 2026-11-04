"""Prompt and SQL execution helpers for the BIRD environment.

Copied from the repo's text2sql package (data.py, evaluate.py, reward.py) so the
environment installs on its own: text2sql isn't on PyPI and must stay
Python 3.8-compatible, while verifiers needs 3.11+. Keep the two in sync.
"""
import re
import sqlite3
import time
from pathlib import Path

SYSTEM_PROMPT = (
    "You are an expert in SQLite. Given a database schema, an optional hint, "
    "and a question, write exactly one SQLite query that answers the question, "
    "using only the tables and columns in the schema. "
    "Return the query in a ```sql code block."
)


def get_schema(db_path):
    """CREATE TABLE statements for every table, read-only."""
    conn = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    finally:
        conn.close()
    return "\n\n".join(row[0] for row in rows)


def build_messages(schema, evidence, question):
    """Prompt v1 (frozen): system instructions + schema, hint, question."""
    user_content = (
        f"### Database schema:\n{schema}\n\n"
        f"### Hint:\n{evidence or 'None'}\n\n"
        f"### Question:\n{question}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def extract_sql(text):
    """The first ```sql block, or None."""
    match = re.search(r"```sql\s*(.*?)```", text, re.DOTALL)
    return None if match is None else match.group(1).strip()


# Row cap for the model's SQL: 10x the gold row count, at least 100,000. A result that
# big can't be the answer, and loading it all could exhaust memory. Gold is never capped
# (two BIRD dev gold answers in card_games return over 100,000 rows).
MIN_ROW_CAP = 100_000


def execute_sql(db_path, sql, timeout=30.0, max_rows=None):
    """Run SQL read-only with a wall-clock timeout and an optional row cap.

    Returns (rows, None), or (None, error) where error is "timeout", "too_many_rows",
    or SQLite's message.
    """
    conn = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
    start = time.monotonic()
    timed_out = False

    def handler():
        nonlocal timed_out
        if time.monotonic() - start > timeout:
            timed_out = True
            return 1  # abort the query
        return 0

    conn.set_progress_handler(handler, 1000)
    try:
        cursor = conn.execute(sql)
        if max_rows is None:
            return cursor.fetchall(), None
        rows = cursor.fetchmany(max_rows + 1)
        if len(rows) > max_rows:
            return None, "too_many_rows"
        return rows, None
    except sqlite3.Error as e:
        return None, "timeout" if timed_out else str(e)
    finally:
        conn.close()


def rows_match(pred_rows, gold_rows):
    """Set comparison, as in BIRD's official script (order and duplicates ignored)."""
    return set(pred_rows) == set(gold_rows)


def is_trivial(rows):
    """Empty result, or a single 0 / 1 / NULL value: what `SELECT 1`-style answers return."""
    if not rows:
        return True
    return len(rows) == 1 and len(rows[0]) == 1 and rows[0][0] in (0, 1, None)


def score(text, db_path, gold_rows, timeout=30.0):
    """Status of one answer: correct, wrong_rows, error, timeout, or no_sql; plus trivial."""
    sql = extract_sql(text)
    if sql is None:
        return "no_sql", False
    cap = max(MIN_ROW_CAP, 10 * len(gold_rows))
    rows, err = execute_sql(db_path, sql, timeout, max_rows=cap)
    if err == "too_many_rows":
        return "wrong_rows", False  # runs, but far too many rows to be the answer
    if err is not None:
        return ("timeout" if err == "timeout" else "error"), False
    return ("correct" if rows_match(rows, gold_rows) else "wrong_rows"), is_trivial(rows)
