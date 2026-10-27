import verifiers.v1 as vf
import asyncio

from text2sql.data import get_db_path, TRAIN_DB_DIR
from text2sql.evaluate import evaluate_one

def resolve_db_path(db_id):
    path = get_db_path(db_id)
    if not path.exists():
        path = get_db_path(db_id, TRAIN_DB_DIR)
    return path


class BirdSqlData(vf.TaskData):
    """One row's data. Add task-specific fields here, such as a reference answer."""
    question_id: int
    db_id: str
    gold_sql: str
    difficulty: str | None = None


class BirdSqlTask(vf.Task[BirdSqlData]):
    """Rewards, hooks, and servers, with row data available on ``self.data``."""
    """Scores one BIRD question by executing the model's SQL against the gold SQL"""
    @vf.reward(weight=1.0)
    async def reward(self, trace: vf.Trace) -> float:
        example = {
            'db_path': resolve_db_path(self.data.db_id),
            'gold_sql': self.data.gold_sql,
        }
        result= await asyncio.to_thread(evaluate_one, trace.last_reply or "", example)
        if result['reward'] is None:
            raise ValueError(f'gold_error on q{self.data.question_id}: {result['error']}')

        return result['reward']

class BirdSqlConfig(vf.TasksetConfig):
    num_tasks: int = 5
    """How many tasks to build."""


class BirdSqlTaskset(vf.Taskset[BirdSqlTask, BirdSqlConfig]):
    def load(self) -> list[BirdSqlTask]:
        raise NotImplementedError(
            "Return this taskset's tasks, e.g. "
            "[BirdSqlTask(BirdSqlData(prompt=...), self.config.task) "
            "for i in range(self.config.num_tasks)]."
        )
