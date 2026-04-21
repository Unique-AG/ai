# %%
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.experimental.scheduled_task import Cron, ScheduledTasks

settings = UniqueSettings.from_env()
scheduled_tasks = ScheduledTasks.from_settings(settings)
task = scheduled_tasks.create(
    cron_expression=Cron.WEEKDAYS_9AM,
    assistant_id="assistant_daily_report",
    prompt="Summarise yesterday's key events and email me the briefing.",
)

print(task.id, task.cron_expression, task.enabled)
updated = scheduled_tasks.update(
    task_id=task.id,
    cron_expression=Cron.EVERY_FIFTEEN_MINUTES,
    enabled=True,
)
scheduled_tasks.update(
    task_id=task.id,
    clear_chat_id=True,
)
