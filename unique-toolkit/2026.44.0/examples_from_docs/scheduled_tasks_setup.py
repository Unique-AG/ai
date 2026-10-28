# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "unique-toolkit>=2026.22.0",
#   "unique-sdk>=2026.22.0",
# ]
# ///

# %%


from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.experimental.resources.scheduled_task import ScheduledTasks

settings = UniqueSettings.from_env()
scheduled_tasks = ScheduledTasks.from_settings(settings)
