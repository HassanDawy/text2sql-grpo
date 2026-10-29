"""GRPO reward: 1.0 if the predicted SQL returns the gold rows, else 0.

Shared by TRL training and the verifiers environment (see NOTES section 8).
"""
import warnings
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from text2sql.data import get_db_path, TRAIN_DB_DIR
from text2sql.evaluate import extract_sql, execute_sql, rows_match


TIMEOUT = 30.0
GOLD_TIMEOUT = 120.0 
WORKERS = 16


def resolve_db_path(db_id):
    """Find a database in the dev folder, then train (no overlap, verified)."""
    path = get_db_path(db_id)
    if not path.exists():
        path = get_db_path(db_id, TRAIN_DB_DIR)
    return path


@lru_cache(maxsize=None)
def gold_rows(db_id, gold_sql):
    """Run each gold query once and cache it. None if it fails.

    A failed gold gives every answer in the group the same reward (0), so the
    advantages are all 0 and the question is effectively skipped, not mis-scored.
    """
    rows, err = execute_sql(resolve_db_path(db_id), gold_sql, GOLD_TIMEOUT)
    if err is not None:
        warnings.warn("gold SQL failed on %s (%s); question skipped" % (db_id, err))
        return None
    return rows


def is_trivial(rows):
    """Empty result, or a single 0 / 1 / NULL value."""
    if not rows:
        return True
    return len(rows) == 1 and len(rows[0]) == 1 and rows[0][0] in (0, 1, None)


@lru_cache(maxsize=65536)
def score(text, db_id, gold_sql):
    """Return (status, trivial) for one completion. Cached so each answer runs once."""
    sql = extract_sql(text)
    if sql is None:
        return "no_sql", False
    gold = gold_rows(db_id, gold_sql)
    if gold is None:
        return "gold_error", False
    rows, err = execute_sql(resolve_db_path(db_id), sql, TIMEOUT)
    if err is not None:
        return ("timeout" if err == "timeout" else "error"), False
    status = "correct" if rows_match(rows, gold) else "wrong_rows"
    return status, is_trivial(rows)


def _text(completion):
    """TRL passes a string, or a list of messages for chat datasets."""
    if isinstance(completion, str):
        return completion
    return completion[-1]["content"]


def _score_batch(completions, db_id, gold_sql):
    args = list(zip([_text(c) for c in completions], db_id, gold_sql))
    # Run each gold query once, one at a time, before the parallel part.
    # Otherwise the 6 answers of a question start the same gold query 6 times at once.
    for pair in dict.fromkeys(zip(db_id, gold_sql)):
        gold_rows(*pair)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return list(pool.map(lambda a: score(*a), args))


def execution_reward(completions, db_id, gold_sql, **kwargs):
    """The GRPO reward (weight 1)."""
    return [1.0 if s == "correct" else 0.0 for s, _ in _score_batch(completions, db_id, gold_sql)]


def error_rate(completions, db_id, gold_sql, **kwargs):
    """Monitoring only (weight 0): error, timeout, or no SQL."""
    return [1.0 if s in ("error", "timeout", "no_sql") else 0.0
            for s, _ in _score_batch(completions, db_id, gold_sql)]


def trivial_rate(completions, db_id, gold_sql, **kwargs):
    """Monitoring only (weight 0): empty or single 0/1/NULL result."""
    return [1.0 if t else 0.0 for _, t in _score_batch(completions, db_id, gold_sql)]