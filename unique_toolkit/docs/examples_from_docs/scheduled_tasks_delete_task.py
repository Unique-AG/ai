# %%
from unique_toolkit.experimental.scheduled_task import Cron, ScheduledTasks

scheduled_tasks = ScheduledTasks.from_settings()
task = scheduled_tasks.create_task(
    cron_expression=Cron.WEEKDAYS_9AM,
    assistant_id="assistant_daily_report",
    prompt="Summarise yesterday's key events and email me the briefing.",
)

print(task.id, task.cron_expression, task.enabled)
ack = scheduled_tasks.delete_task(task_id=task.id)
assert ack.deleted is True
