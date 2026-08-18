class InputTokenBudgetExceededError(Exception):
    """Raised when an input payload cannot be reduced to the model budget."""

    def __init__(
        self,
        *,
        token_count: int,
        token_budget: int,
        reserved_input_tokens: int = 0,
    ) -> None:
        self.token_count = token_count
        self.token_budget = token_budget
        self.reserved_input_tokens = reserved_input_tokens
        super().__init__(
            f"Input payload uses {token_count} tokens but the adjusted budget is "
            f"{token_budget} tokens ({reserved_input_tokens} tokens reserved)."
        )
