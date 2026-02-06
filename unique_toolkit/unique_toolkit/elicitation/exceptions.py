def _format_exception_context(context: str, instruction: str) -> str:
    if context:
        return f"Exception Context: {context}.  Instruction: {instruction}"
    else:
        return f"Instruction: {instruction}"


class _ElicitationException(Exception):
    """Base exception for elicitation-related errors.

    This exception is raised when there's an issue during the elicitation process,
    where additional information is requested from the user.
    """

    INSTRUCTION = (
        "The tool failed to finish the elicitation process."
        "Please inform the user that there was an issue obtaining the required information. "
        "Ask if they would like to try again or if they need assistance in a different way."
    )

    def __init__(self, context: str = "", instruction: str = INSTRUCTION):
        message = _format_exception_context(context, instruction)

        super().__init__(message)


class ElicitationDeclinedException(_ElicitationException):
    """Exception raised when a user explicitly cancels an elicitation request.

    This indicates that the user has chosen not to provide the requested information.
    """

    INSTRUCTION = (
        "The user has declined the elicitation request. "
        "Please inform the user that you understand they chose not to provide the requested information at this time. "
        "Ask if there is anything you can help clarify or adjust about the request to make it more acceptable, "
        "or if there is an alternative approach they would prefer to accomplish their goal."
    )

    def __init__(self, context: str = "", instruction: str = INSTRUCTION):
        message = _format_exception_context(context, instruction)

        super().__init__(message)


class ElicitationCancelledException(_ElicitationException):
    """Exception raised when a user explicitly cancels an elicitation request.

    This indicates that the user has chosen not to provide the requested information.
    """

    INSTRUCTION = (
        "The user has cancelled the elicitation request. "
        "Please inform the user that you understand they chose not to provide the requested information at this time. "
        "Ask if there is anything you can help clarify or adjust about the request to make it more acceptable, "
        "or if there is an alternative approach they would prefer to accomplish their goal."
    )

    def __init__(self, context: str = "", instruction: str = INSTRUCTION):
        message = _format_exception_context(context, instruction)

        super().__init__(message)


class ElicitationExpiredException(_ElicitationException):
    """Exception raised when an elicitation request expires without a response.

    This indicates that the user did not respond within the allowed time frame.
    """

    INSTRUCTION = (
        "The elicitation request has expired without receiving a response from the user. "
        "Please inform the user that the request timed out and apologize for any inconvenience. "
        "Ask if they would like you to resend the request or if they need more time to gather the required information. "
        "Offer to help in any other way that might be more convenient for them."
    )

    def __init__(self, context: str = "", instruction: str = INSTRUCTION):
        message = _format_exception_context(context, instruction)

        super().__init__(message)


class ElicitationFailedException(_ElicitationException):
    """Exception raised when an elicitation request fails.

    This indicates that the elicitation request failed to be created or received a response.
    """

    INSTRUCTION = (
        "The elicitation request failed to be created or received a response. "
        "Please inform the user that there was an issue obtaining the required information. "
        "Ask if they would like to try again or if they need assistance in a different way."
    )

    def __init__(self, context: str = "", instruction: str = INSTRUCTION):
        message = _format_exception_context(context, instruction)

        super().__init__(message)
