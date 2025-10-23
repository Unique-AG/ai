from urllib.parse import quote


def create_prompt_button_string(
    *,
    button_text: str,
    next_user_message: str,
) -> str:
    """
    Create a prompt button string.

    Args:
        button_text: The text of the button.
        next_user_message: The message to send when the button is clicked.

    Returns:
        A string that can be used to create a prompt button.
        A prompt button includes the `next_user_message` to the user prompt windown.
    """
    next_user_message = quote(next_user_message)
    return f"[{button_text}](https://prompt={next_user_message})"


def create_latex_formula_string(latex_expression: str) -> str:
    """
    Create a LaTeX string.

    Args:
        latex_expression: The LaTeX expression to create.

    Returns:
        A string that can be used to create a LaTeX string.
    """
    return f"\\[{latex_expression}\\]"
