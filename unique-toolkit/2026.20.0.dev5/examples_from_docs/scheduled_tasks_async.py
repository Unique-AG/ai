# %%
import asyncio

from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.experimental.scheduled_task import Cron, ScheduledTasks

settings = UniqueSettings.from_env()
scheduled_tasks = ScheduledTasks.from_settings(settings)


async def main() -> None:
    task = await scheduled_tasks.create_async(
        cron_expression=Cron.HOURLY,
        assistant_id="assistant_hourly_digest",
        prompt="Write a one-paragraph digest of the past hour.",
    )

    await scheduled_tasks.list_async()
    await scheduled_tasks.delete_async(task_id=task.id)


asyncio.run(main())
