import re
from typing import Literal

from unique_toolkit.agentic.tools.a2a.postprocessing.config import (
    SubAgentResponseDisplayMode,
)


def _wrap_with_html_block(text: str, start_tag: str, end_tag: str) -> str:
    text = text.strip()
    start_tag = start_tag.strip()
    end_tag = end_tag.strip()

    if start_tag != "":
        start_tag = f"{start_tag}\n"

    if end_tag != "":
        end_tag = f"\n{end_tag}"

    return f"{start_tag}{text}{end_tag}"


def _join_html_blocks(*blocks: str) -> str:
    return "\n".join(block.strip() for block in blocks)


def _wrap_with_details_tag(
    text, mode: Literal["open", "closed"], summary_name: str | None = None
) -> str:
    if summary_name is not None:
        summary_tag = _wrap_with_html_block(summary_name, "<summary>", "</summary>")
        text = _join_html_blocks(summary_tag, text)

    if mode == "open":
        text = _wrap_with_html_block(text, "<details open>", "</details>")
    else:
        text = _wrap_with_html_block(text, "<details>", "</details>")

    return text


_BLOCK_BORDER_STYLE = (
    "overflow-y: auto; border: 1px solid #ccc; padding: 8px; margin-top: 8px;"
)


def _wrap_with_block_border(text: str) -> str:
    return _wrap_with_html_block(text, f"<div style='{_BLOCK_BORDER_STYLE}'>", "</div>")


_QUOTE_BORDER_STYLE = (
    "margin-left: 20px; border-left: 2px solid #ccc; padding-left: 10px;"
)


def _wrap_with_quote_border(text: str) -> str:
    return _wrap_with_html_block(text, f"<div style='{_QUOTE_BORDER_STYLE}'>", "</div>")


def _wrap_strong(text: str) -> str:
    return _wrap_with_html_block(text, "<strong>", "</strong>")


def _wrap_hidden_div(text: str) -> str:
    return _wrap_with_html_block(text, '<div style="display: none;">', "</div>")


def _add_line_break(text: str, before: bool = True, after: bool = True) -> str:
    start_tag = ""
    if before:
        start_tag = "<br>"

    end_tag = ""
    if after:
        end_tag = "<br>"

    return _wrap_with_html_block(text, start_tag, end_tag)


def _get_display_template(
    mode: SubAgentResponseDisplayMode,
    add_quote_border: bool,
    add_block_border: bool,
    answer_placeholder: str = "answer",
    assistant_id_placeholder: str = "assistant_id",
    display_name_placeholder: str = "display_name",
) -> str:
    if mode == SubAgentResponseDisplayMode.HIDDEN:
        return ""

    assistant_id_placeholder = _wrap_hidden_div("{%s}" % assistant_id_placeholder)
    display_name_placeholder = _wrap_strong("{%s}" % display_name_placeholder)
    template = _join_html_blocks(assistant_id_placeholder, "{%s}" % answer_placeholder)

    if add_quote_border:
        template = _wrap_with_quote_border(template)

    match mode:
        case SubAgentResponseDisplayMode.DETAILS_OPEN:
            template = _wrap_with_details_tag(
                template, "open", display_name_placeholder
            )
        case SubAgentResponseDisplayMode.DETAILS_CLOSED:
            template = _wrap_with_details_tag(
                template, "closed", display_name_placeholder
            )
        case SubAgentResponseDisplayMode.PLAIN:
            display_name_placeholder = _add_line_break(
                display_name_placeholder, before=False, after=True
            )
            template = _join_html_blocks(display_name_placeholder, template)
            # Add a hidden block border to seperate sub agent answers from the rest of the text.
            hidden_block_border = _wrap_hidden_div("sub_agent_answer_block")
            template = _join_html_blocks(template, hidden_block_border)

    if add_block_border:
        template = _wrap_with_block_border(template)

    return template


def _get_display_removal_re(
    assistant_id: str,
    mode: SubAgentResponseDisplayMode,
    add_quote_border: bool,
    add_block_border: bool,
) -> re.Pattern[str]:
    template = _get_display_template(
        mode=mode,
        add_quote_border=add_quote_border,
        add_block_border=add_block_border,
    )

    pattern = template.format(
        assistant_id=re.escape(assistant_id), answer=r"(.*?)", display_name=r"(.*?)"
    )

    return re.compile(pattern, flags=re.DOTALL)


def _build_sub_agent_answer_display(
    display_name: str,
    display_mode: SubAgentResponseDisplayMode,
    add_quote_border: bool,
    add_block_border: bool,
    answer: str,
    assistant_id: str,
) -> str:
    template = _get_display_template(
        mode=display_mode,
        add_quote_border=add_quote_border,
        add_block_border=add_block_border,
    )
    return template.format(
        display_name=display_name, answer=answer, assistant_id=assistant_id
    )


def _remove_sub_agent_answer_from_text(
    display_mode: SubAgentResponseDisplayMode,
    add_quote_border: bool,
    add_block_border: bool,
    text: str,
    assistant_id: str,
) -> str:
    pattern = _get_display_removal_re(
        assistant_id=assistant_id,
        mode=display_mode,
        add_quote_border=add_quote_border,
        add_block_border=add_block_border,
    )
    return re.sub(pattern, "", text)
