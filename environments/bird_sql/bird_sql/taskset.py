import verifiers.v1 as vf


class BirdSqlData(vf.TaskData):
    """One row's data. Add task-specific fields here, such as a reference answer."""


class BirdSqlTask(vf.Task[BirdSqlData]):
    """Rewards, hooks, and servers, with row data available on ``self.data``."""
    @vf.reward(weight=1.0)
    async def reward(self, trace: vf.Trace) -> float:
        raise NotImplementedError("Score the rollout and return a float (e.g. in [0, 1]).")


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
