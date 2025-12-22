import logging
from typing import Optional

from unique_toolkit.app.schemas import Event


class BaseService:
    def __init__(self, event: Event, logger: Optional[logging.Logger] = None):
        self.event = event
        self.logger = logger or logging.getLogger(__name__)


# some changes to trigger the changelog enforcement
