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
