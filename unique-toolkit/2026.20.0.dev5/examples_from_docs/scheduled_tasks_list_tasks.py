# %%
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.experimental.scheduled_task import ScheduledTasks

settings = UniqueSettings.from_env()
scheduled_tasks = ScheduledTasks.from_settings(settings)
for task in scheduled_tasks.list():
    print(task.id, task.cron_expression, task.prompt[:40])

detail = scheduled_tasks.get(task_id=task.id)
