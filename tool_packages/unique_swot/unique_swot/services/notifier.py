from abc import ABC, abstractmethod
from logging import getLogger

logger = getLogger(__name__)

class Notifier(ABC):
    @abstractmethod
    def notify(self, step_name: str, progress: float) -> None:
        assert 0 <= progress <= 1
        raise NotImplementedError


# TODO: Implement a real notifier
class LoggerNotifier(Notifier):
    def notify(self, step_name: str, progress: float) -> None:
        logger.info(f"{step_name}: {progress}")