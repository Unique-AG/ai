# %%
from unique_toolkit.experimental.scheduled_task import ScheduledTasks

scheduled_tasks = ScheduledTasks.from_settings()
for task in scheduled_tasks.list_tasks():
    print(task.id, task.cron_expression, task.prompt[:40])

detail = scheduled_tasks.get_task(task_id=task.id)
