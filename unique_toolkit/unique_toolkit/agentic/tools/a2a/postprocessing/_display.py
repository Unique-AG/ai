import re
from abc import ABC, abstractmethod
from typing import Literal, override

from unique_toolkit.agentic.tools.a2a.postprocessing.config import (
    SubAgentResponseDisplayMode,
)


class _ResponseDisplayHandler(ABC):
    @abstractmethod
    def build_response_display(
        self, display_name: str, assistant_id: str, answer: str
    ) -> str:
        raise NotImplementedError()

    @abstractmethod
    def remove_response_display(self, assistant_id: str, text: str) -> str:
        raise NotImplementedError()


class _DetailsResponseDisplayHandler(_ResponseDisplayHandler):
    def __init__(self, mode: Literal["open", "closed"]) -> None:
        self._mode = mode

    DETAILS_CLOSED_TEMPLATE = (
        "<details><summary>{display_name}</summary>\n"
        "\n"
        '<div style="display: none;">{assistant_id}</div>\n'
        "\n"
        "{answer}\n"
        "</details>\n"
        "<br>\n"
        "\n"
    )

    DETAILS_OPEN_TEMPLATE = (
        "<details open><summary>{display_name}</summary>\n"
        "\n"
        '<div style="display: none;">{assistant_id}</div>\n'
        "\n"
        "{answer}\n"
        "\n"
        "</details>\n"
        "<br>\n"
        "\n"
    )

    def _get_detect_re(self, assistant_id: str) -> str:
        if self._mode == "open":
            return (
                r"(?s)<details open>\s*"
                r"<summary>(.*?)</summary>\s*"
                rf"<div style=\"display: none;\">{re.escape(assistant_id)}</div>\s*"
                r"(.*?)\s*"
                r"</details>\s*"
                r"<br>\s*"
            )
        else:
            return (
                r"(?s)<details>\s*"
                r"<summary>(.*?)</summary>\s*"
                rf"<div style=\"display: none;\">{re.escape(assistant_id)}</div>\s*"
                r"(.*?)\s*"
                r"</details>\s*"
                r"<br>\s*"
            )

    def _get_template(self) -> str:
        if self._mode == "open":
            return self.DETAILS_OPEN_TEMPLATE
        else:
            return self.DETAILS_CLOSED_TEMPLATE

    @override
    def build_response_display(
        self, display_name: str, assistant_id: str, answer: str
    ) -> str:
        return self._get_template().format(
            assistant_id=assistant_id, display_name=display_name, answer=answer
        )

    @override
    def remove_response_display(self, assistant_id: str, text: str) -> str:
        return re.sub(self._get_detect_re(assistant_id=assistant_id), "", text)


_DISPLAY_HANDLERS = {
    SubAgentResponseDisplayMode.DETAILS_OPEN: _DetailsResponseDisplayHandler(
        mode="open"
    ),
    SubAgentResponseDisplayMode.DETAILS_CLOSED: _DetailsResponseDisplayHandler(
        mode="closed"
    ),
}


def _build_sub_agent_answer_display(
    display_name: str,
    display_mode: SubAgentResponseDisplayMode,
    answer: str,
    assistant_id: str,
) -> str:
    if display_mode not in _DISPLAY_HANDLERS:
        return ""

    display_f = _DISPLAY_HANDLERS[display_mode]

    return display_f.build_response_display(
        display_name=display_name, answer=answer, assistant_id=assistant_id
    )


def _remove_sub_agent_answer_from_text(
    display_mode: SubAgentResponseDisplayMode, text: str, assistant_id: str
) -> str:
    if display_mode not in _DISPLAY_HANDLERS:
        return text

    display_f = _DISPLAY_HANDLERS[display_mode]

    return display_f.remove_response_display(assistant_id=assistant_id, text=text)
