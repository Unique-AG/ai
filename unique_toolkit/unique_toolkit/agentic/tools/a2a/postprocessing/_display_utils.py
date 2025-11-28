import re
from typing import Literal, NamedTuple

from unique_toolkit._common.utils.jinja.render import render_template
from unique_toolkit.agentic.tools.a2a.postprocessing.config import (
    SubAgentDisplayConfig,
    SubAgentResponseDisplayMode,
)


def _wrap_text(text: str, start_text: str, end_text: str) -> str:
    text = text.strip()
    start_text = start_text.strip()
    end_text = end_text.strip()

    if start_text != "":
        start_text = f"{start_text}\n"

    if end_text != "":
        end_text = f"\n{end_text}"

    return f"{start_text}{text}{end_text}"


def _join_text_blocks(*blocks: str, sep: str = "\n") -> str:
    return sep.join(block.strip() for block in blocks)


def _wrap_with_details_tag(
    text, mode: Literal["open", "closed"], summary_name: str | None = None
) -> str:
    if summary_name is not None:
        summary_tag = _wrap_text(summary_name, "<summary>", "</summary>")
        text = _join_text_blocks(summary_tag, text)

    if mode == "open":
        text = _wrap_text(text, "<details open>", "</details>")
    else:
        text = _wrap_text(text, "<details>", "</details>")

    return text


_BLOCK_BORDER_STYLE = (
    "overflow-y: auto; border: 1px solid #ccc; padding: 8px; margin-top: 8px;"
)


def _wrap_with_block_border(text: str) -> str:
    return _wrap_text(text, f"<div style='{_BLOCK_BORDER_STYLE}'>", "</div>")


_QUOTE_BORDER_STYLE = (
    "margin-left: 20px; border-left: 2px solid #ccc; padding-left: 10px;"
)


def _wrap_with_quote_border(text: str) -> str:
    return _wrap_text(text, f"<div style='{_QUOTE_BORDER_STYLE}'>", "</div>")


def _wrap_strong(text: str) -> str:
    return _wrap_text(text, "<strong>", "</strong>")


def _wrap_hidden_div(text: str) -> str:
    return _wrap_text(text, '<div style="display: none;">', "</div>")


def _add_line_break(text: str, before: bool = True, after: bool = True) -> str:
    start_tag = ""
    if before:
        start_tag = "<br>"

    end_tag = ""
    if after:
        end_tag = "<br>"

    return _wrap_text(text, start_tag, end_tag)


def _prepare_title_template(
    display_title_template: str, display_name_placeholder: str
) -> str:
    return display_title_template.replace("{}", "{%s}" % display_name_placeholder)


def _clean_linebreaks(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^(<br>)*|(<br>)*$", "", text)
    return text


def _get_display_template(
    mode: SubAgentResponseDisplayMode,
    add_quote_border: bool,
    add_block_border: bool,
    display_title_template: str,
    answer_placeholder: str = "answer",
    assistant_id_placeholder: str = "assistant_id",
    display_name_placeholder: str = "display_name",
) -> str:
    if mode == SubAgentResponseDisplayMode.HIDDEN:
        return ""

    assistant_id_placeholder = _wrap_hidden_div("{%s}" % assistant_id_placeholder)
    title_template = _prepare_title_template(
        display_title_template, display_name_placeholder
    )
    template = _join_text_blocks(
        assistant_id_placeholder, "{%s}" % answer_placeholder, sep="\n\n"
    )  # Double line break is needed for markdown formatting

    template = _add_line_break(template, before=True, after=False)

    if add_quote_border:
        template = _wrap_with_quote_border(template)

    match mode:
        case SubAgentResponseDisplayMode.DETAILS_OPEN:
            template = _wrap_with_details_tag(
                template,
                "open",
                title_template,
            )
        case SubAgentResponseDisplayMode.DETAILS_CLOSED:
            template = _wrap_with_details_tag(template, "closed", title_template)
        case SubAgentResponseDisplayMode.PLAIN:
            # Add a hidden block border to seperate sub agent answers from the rest of the text.
            hidden_block_border = _wrap_hidden_div("sub_agent_answer_block")
            template = _join_text_blocks(title_template, template, hidden_block_border)

    if add_block_border:
        template = _wrap_with_block_border(template)

    return _clean_linebreaks(template)


def _get_display_removal_re(
    assistant_id: str,
    mode: SubAgentResponseDisplayMode,
    add_quote_border: bool,
    add_block_border: bool,
    display_title_template: str,
) -> re.Pattern[str]:
    template = _get_display_template(
        mode=mode,
        add_quote_border=add_quote_border,
        add_block_border=add_block_border,
        display_title_template=display_title_template,
    )

    pattern = template.format(
        assistant_id=re.escape(assistant_id), answer=r"(.*?)", display_name=r"(.*?)"
    )

    return re.compile(pattern, flags=re.DOTALL)


class SubAgentAnswerPart(NamedTuple):
    matching_text: str  # Matching text as found in the answer
    formatted_text: str  # Formatted text to be displayed


def get_sub_agent_answer_parts(
    answer: str,
    display_config: SubAgentDisplayConfig,
) -> list[SubAgentAnswerPart]:
    if display_config.mode == SubAgentResponseDisplayMode.HIDDEN:
        return []

    if len(display_config.answer_substrings_config) == 0:
        return [SubAgentAnswerPart(matching_text=answer, formatted_text=answer)]

    substrings = []
    for config in display_config.answer_substrings_config:
        for match in config.regexp.finditer(answer):
            text = match.group(0)
            substrings.append(
                SubAgentAnswerPart(
                    matching_text=text,
                    formatted_text=config.display_template.format(text),
                )
            )

    return substrings


def get_sub_agent_answer_from_parts(
    answer_parts: list[SubAgentAnswerPart],
    config: SubAgentDisplayConfig,
) -> str:
    return render_template(
        config.answer_substrings_jinja_template,
        {
            "substrings": [answer.formatted_text for answer in answer_parts],
        },
    )


def get_sub_agent_answer_display(
    display_name: str,
    display_config: SubAgentDisplayConfig,
    answer: str | list[SubAgentAnswerPart],
    assistant_id: str,
) -> str:
    template = _get_display_template(
        mode=display_config.mode,
        add_quote_border=display_config.add_quote_border,
        add_block_border=display_config.add_block_border,
        display_title_template=display_config.display_title_template,
    )

    if isinstance(answer, list):
        answer = get_sub_agent_answer_from_parts(
            answer_parts=answer,
            config=display_config,
        )

    return template.format(
        display_name=display_name, answer=answer, assistant_id=assistant_id
    )


def remove_sub_agent_answer_from_text(
    display_config: SubAgentDisplayConfig,
    text: str,
    assistant_id: str,
) -> str:
    if not display_config.remove_from_history:
        return text

    pattern = _get_display_removal_re(
        assistant_id=assistant_id,
        mode=display_config.mode,
        add_quote_border=display_config.add_quote_border,
        add_block_border=display_config.add_block_border,
        display_title_template=display_config.display_title_template,
    )
    return re.sub(pattern, "", text)
