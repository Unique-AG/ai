import json
from typing import Any
from urllib.parse import quote as encodeURIComponent

from jinja2 import Template
from unique_toolkit.language_model import LanguageModelMessage

from unique_follow_up_questions.schema import FollowUpQuestion, FollowUpQuestionsOutput
from unique_follow_up_questions.utils.jinja.helpers import get_parent_dir, load_template
from unique_follow_up_questions.utils.jinja.schema import Jinja2PromptParams




PARENT_DIR = get_parent_dir(__file__)

FOLLOW_UP_QUESTION_SYSTEM_PROMPT_TEMPLATE = load_template(
    PARENT_DIR, "system_prompt.j2"
)

FOLLOW_UP_QUESTION_USER_PROMPT_TEMPLATE = load_template(
    PARENT_DIR, "user_prompt.j2"
)

SUGGESTION_FORMAT_TEMPLATE = load_template(PARENT_DIR, "suggestions_format.j2")


class FollowUpQuestionSystemPromptParams(Jinja2PromptParams):
    output_schema: str = json.dumps(
        FollowUpQuestionsOutput.model_json_schema(), indent=2
    )
    examples: list[FollowUpQuestion]
    number_of_questions: int


class FollowUpQuestionUserPromptParams(Jinja2PromptParams):
    conversation_history: list[LanguageModelMessage]
    additional_context: str | None
    language: str | None

    def render_template(self, template: str) -> str:
        return super().render_template(template)


class FollowUpQuestionResponseParams(Jinja2PromptParams):
    questions: list[str]

    def custom_model_dump(self) -> dict[str, Any]:
        questions = []
        for question in self.questions:
            questions.append(
                {
                    "question": question,
                    "encoded_uri": encodeURIComponent(question),
                }
            )

        return {"questions": questions}

    def render_template(self, template: str) -> str:
        params = self.custom_model_dump()

        return Template(template, lstrip_blocks=True).render(**params)
