import logging
from typing import Optional

from unique_toolkit.chat.state import ChatState


class BaseService:
    def __init__(self, state: ChatState, logger: Optional[logging.Logger] = None):
        self.state = state
        self.logger = logger or logging.getLogger(__name__)
