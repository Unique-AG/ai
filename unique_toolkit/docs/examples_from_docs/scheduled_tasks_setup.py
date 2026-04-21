# %%
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.experimental.scheduled_task import ScheduledTasks

settings = UniqueSettings.from_env()
scheduled_tasks = ScheduledTasks.from_settings(settings)
