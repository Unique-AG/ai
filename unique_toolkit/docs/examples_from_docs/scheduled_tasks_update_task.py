# %%
from unique_toolkit.experimental.scheduled_task import Cron, ScheduledTasks

scheduled_tasks = ScheduledTasks.from_settings()
task = scheduled_tasks.create_task(
    cron_expression=Cron.WEEKDAYS_9AM,
    assistant_id="assistant_daily_report",
    prompt="Summarise yesterday's key events and email me the briefing.",
)

print(task.id, task.cron_expression, task.enabled)
updated = scheduled_tasks.update_task(
    task_id=task.id,
    cron_expression=Cron.EVERY_FIFTEEN_MINUTES,
    enabled=True,
)
scheduled_tasks.update_task(
    task_id=task.id,
    clear_chat_id=True,
)
