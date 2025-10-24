from typing import Optional


class CommonException(Exception):
    def __init__(
        self,
        user_message: str,
        error_message: str,
        exception: Optional[Exception] = None,
    ):
        super().__init__(error_message)
        self._user_message = user_message
        self._error_message = error_message
        self._exception = exception

    @property
    def user_message(self):
        return self._user_message

    @property
    def error_message(self):
        return self._error_message

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def exception(self):
        return self._exception

    def __str__(self):
        return self._error_message


class ConfigurationException(Exception):
    pass


class InfoExceptionForAi(Exception):
    """
    This exception is raised as information to the AI.
    Such that it can be used to inform the user about the error.
    In a meaningful way.
    """

    def __init__(
        self,
        error_message: str,
        message_for_ai: str,
    ):
        super().__init__(error_message)
        self._message_for_ai = message_for_ai

    @property
    def message_for_ai(self):
        return self._message_for_ai
