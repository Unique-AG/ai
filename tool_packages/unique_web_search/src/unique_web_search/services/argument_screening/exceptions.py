class ArgumentScreeningException(Exception):
    """Raised when the screening agent blocks a tool call."""

    INSTRUCTION = (
        "The tool call was blocked by the argument screening agent because "
        "the provided arguments were flagged as containing sensitive or "
        "inappropriate content. Inform the user that the search was not "
        "executed and explain the reason. Ask if they would like to rephrase "
        "their request without the flagged content."
    )

    def __init__(self, reason: str, instruction: str = INSTRUCTION):
        message = f"Exception Context: {reason}.  Instruction: {instruction}"
        super().__init__(message)
