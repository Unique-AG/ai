class ArgumentScreeningUnparseableResponseException(Exception):
    """Raised when the screening agent returns an unparseable response."""

    INSTRUCTION = (
        "The screening agent returned an unparseable response. As a conservative approach, the webSearch "
        "tool has been blocked. Inform the user that the search was not executed and explain the reason. "
        "Ask if they would like to rephrase their request without the flagged content."
    )

    def __init__(self, reason: str, instruction: str = INSTRUCTION):
        message = f"Exception Context: {reason}.  Instruction: {instruction}"
        super().__init__(message)
