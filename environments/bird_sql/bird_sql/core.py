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


def _connect(db_path, timeout):
    """Read-only connection that aborts any query running longer than `timeout` seconds.
    Returns (conn, timed_out) where timed_out() says whether the abort fired."""
    conn = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
    start = time.monotonic()
    state = {"timed_out": False}

    def handler():
        if time.monotonic() - start > timeout:
            state["timed_out"] = True
            return 1  # abort the query
        return 0

    conn.set_progress_handler(handler, 1000)
    return conn, lambda: state["timed_out"]


def execute_sql(db_path, sql, timeout=30.0):
    """Run SQL read-only with a wall-clock timeout. Returns (rows, None) or (None, error)."""
    conn, timed_out = _connect(db_path, timeout)
    try:
        return conn.execute(sql).fetchall(), None
    except sqlite3.Error as e:
        return None, "timeout" if timed_out() else str(e)
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
    """Status of one answer: correct, wrong_rows, error, timeout, or no_sql; plus trivial.

    Same result as fetching every row and comparing sets (BIRD's rule), but streams the
    answer's rows: it stops at the first row that isn't in the gold set (the sets can't
    be equal then), and otherwise only keeps rows that are in the gold set. So a query
    returning millions of rows can't exhaust memory, and one returning millions of
    duplicates of the right rows still scores correct.
    """
    sql = extract_sql(text)
    if sql is None:
        return "no_sql", False
    gold = set(gold_rows)
    conn, timed_out = _connect(db_path, timeout)
    try:
        cursor = conn.execute(sql)
        seen, n, first = set(), 0, None
        while True:
            chunk = cursor.fetchmany(10_000)
            if not chunk:
                break
            for row in chunk:
                n += 1
                if n == 1:
                    first = row
                if row not in gold:
                    single = n == 1 and len(chunk) == 1 and not cursor.fetchmany(1)
                    return "wrong_rows", single and _trivial_row(first)
                seen.add(row)
    except sqlite3.Error as e:
        return ("timeout" if timed_out() else "error"), False
    finally:
        conn.close()
    trivial = n == 0 or (n == 1 and _trivial_row(first))
    return ("correct" if seen == gold else "wrong_rows"), trivial


def _trivial_row(row):
    return len(row) == 1 and row[0] in (0, 1, None)
