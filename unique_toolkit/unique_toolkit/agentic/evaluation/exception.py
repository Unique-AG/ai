from unique_toolkit._common.exception import CommonException
from unique_toolkit.language_model.invocation_stats import LanguageModelInvocationStats


class EvaluatorException(CommonException):
    def __init__(
        self,
        user_message: str,
        error_message: str,
        exception: Exception | None = None,
        invocation_stats: list[LanguageModelInvocationStats] | None = None,
    ) -> None:
        super().__init__(
            user_message=user_message,
            error_message=error_message,
            exception=exception,
        )
        # Carries whatever usage was already captured before the failure, so a
        # successful (billable) LLM call isn't silently dropped from the report
        # just because something after it (parsing, validation) raised.
        self.invocation_stats: list[LanguageModelInvocationStats] = (
            invocation_stats or []
        )
