"""BIRD text-to-SQL taskset: one question per task, scored by executing the SQL."""
import asyncio
import json
import logging
import os
from functools import lru_cache
from pathlib import Path

import verifiers.v1 as vf

from bird_sql.core import build_messages, execute_sql, get_schema, score

logger = logging.getLogger(__name__)

SQL_TIMEOUT = 30.0    # model's SQL
GOLD_TIMEOUT = 120.0  # gold SQL: known to run, but slow on some SQLite versions / busy CPUs

# Train gold queries that fail or time out on SQLite 3.35.5 (30 s); excluded from the train split.
TRAIN_GOLD_FAILURES = Path(__file__).parent / "train_gold_failures.txt"


@lru_cache(maxsize=None)
def gold_rows(db_path, gold_sql):
    """Run each gold query once per process and cache it. None if it fails."""
    rows, err = execute_sql(db_path, gold_sql, GOLD_TIMEOUT)
    if err is not None:
        logger.warning("gold SQL failed on %s (%s)", Path(db_path).stem, err)
        return None
    return rows


def score_answer(text, db_path, gold_sql):
    gold = gold_rows(db_path, gold_sql)
    if gold is None:
        return "gold_error", False
    return score(text, db_path, gold, SQL_TIMEOUT)


class BirdSqlData(vf.TaskData):
    question_id: int
    db_id: str
    db_path: str
    gold_sql: str
    difficulty: str | None = None  # None for train


class BirdSqlTask(vf.Task[BirdSqlData]):
    """Reward: 1 if the answer's rows match the gold rows, else 0.

    Metrics (recorded, not part of the reward): error (SQL error, timeout or no SQL),
    trivial (empty or single 0/1/NULL result, the `SELECT 1` reward-hacking signal),
    and gold_error (the gold query itself failed; the answer then scores 0).
    """

    def _result(self, trace):
        """Score each answer once; the reward and metrics run concurrently and share it."""
        text = trace.last_reply or ""
        cache = self.__dict__.setdefault("_results", {})
        if text not in cache:
            cache[text] = asyncio.ensure_future(asyncio.to_thread(
                score_answer, text, self.data.db_path, self.data.gold_sql))
        return cache[text]

    @vf.reward(weight=1.0)
    async def execution_match(self, trace: vf.Trace) -> float:
        status, _ = await self._result(trace)
        return 1.0 if status == "correct" else 0.0

    @vf.metric
    async def error(self, trace: vf.Trace) -> float:
        status, _ = await self._result(trace)
        return 1.0 if status in ("error", "timeout", "no_sql") else 0.0

    @vf.metric
    async def trivial(self, trace: vf.Trace) -> float:
        _, trivial = await self._result(trace)
        return 1.0 if trivial else 0.0

    @vf.metric
    async def gold_error(self, trace: vf.Trace) -> float:
        status, _ = await self._result(trace)
        return 1.0 if status == "gold_error" else 0.0


class BirdSqlConfig(vf.TasksetConfig):
    split: str = "dev"
    """dev (1,534 questions) or train (9,428 minus 377 broken gold queries)."""
    data_dir: str | None = None
    """BIRD split folder (contains dev.json or train.json). Defaults to $BIRD_DIR for dev
    and $BIRD_TRAIN_DIR for train."""
    num_tasks: int | None = None
    """Use only the first N questions."""


class BirdSqlTaskset(vf.Taskset[BirdSqlTask, BirdSqlConfig]):
    def load(self) -> list[BirdSqlTask]:
        split = self.config.split
        if split not in ("dev", "train"):
            raise ValueError(f"Unknown split: {split} (use dev or train)")

        env_var = "BIRD_DIR" if split == "dev" else "BIRD_TRAIN_DIR"
        data_dir = self.config.data_dir or os.environ.get(env_var)
        if not data_dir:
            raise ValueError(f"Set --env.taskset.data-dir or ${env_var} to the BIRD {split} folder")
        data_dir = Path(data_dir)
        db_dir = data_dir / f"{split}_databases" / f"{split}_databases"

        with open(data_dir / f"{split}.json") as f:
            rows = json.load(f)

        skip = set()
        if split == "train":
            with open(TRAIN_GOLD_FAILURES) as f:
                skip = {int(line.split(":")[0][1:]) for line in f if line.strip()}

        tasks, schemas = [], {}
        for i, row in enumerate(rows):
            qid = row.get("question_id", i)  # train has no ids: use position
            if qid in skip:
                continue
            db_id = row["db_id"]
            db_path = db_dir / db_id / f"{db_id}.sqlite"
            if db_id not in schemas:
                schemas[db_id] = get_schema(db_path)
            tasks.append(BirdSqlTask(
                BirdSqlData(
                    prompt=build_messages(schemas[db_id], row["evidence"], row["question"]),
                    question_id=qid,
                    db_id=db_id,
                    db_path=str(db_path),
                    gold_sql=row["SQL"],
                    difficulty=row.get("difficulty"),
                ),
                self.config.task,
            ))
            if self.config.num_tasks is not None and len(tasks) == self.config.num_tasks:
                break
        return tasks
