import verifiers.v1 as vf
import asyncio

from text2sql.data import get_db_path, load_examples, build_messages, TRAIN_DB_DIR, HERE, BIRD_DIR, BIRD_TRAIN_DIR
from text2sql.evaluate import evaluate_one

from pathlib import Path

REPO_ROOT = HERE.parent

def load_failed_ids(split): 
    path = REPO_ROOT / 'results' / f'check_gold_{split}_failures.txt'
    if not path.exists():
        return set()
    with open(path) as f:
        # each line looks like "q123: gold_error | ..."
        return {int(line.split(':')[0][1:]) for line in f if line.strip()}

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
    split: str = 'dev'
    num_tasks: int | None = None
    """How many tasks to build."""



class BirdSqlTaskset(vf.Taskset[BirdSqlTask, BirdSqlConfig]):
    def load(self) -> list[BirdSqlTask]:
        split = self.config.split
        if split == 'dev':
            examples = load_examples(BIRD_DIR / 'dev.json')
        elif split == 'train': 
            examples = load_examples(BIRD_TRAIN_DIR / 'train.json', TRAIN_DB_DIR)
        else:
            raise ValueError(f'Unknown split: {split}')

        failed = load_failed_ids(split)
        examples = [ex for ex in examples if ex['question_id'] not in failed]

        if self.config.num_tasks is not None:
            examples = examples[: self.config.num_tasks]

        return [
            BirdSqlTask(
                BirdSqlData(
                    prompt=build_messages(ex),
                    question_id=ex['question_id'],
                    db_id=Path(ex['db_path']).stem,
                    gold_sql=ex['gold_sql'],
                    difficulty=ex['difficulty'],
                ),
                self.config.task,
            )
            for ex in examples
        ]
