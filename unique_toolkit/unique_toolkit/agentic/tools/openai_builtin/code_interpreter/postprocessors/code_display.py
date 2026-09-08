import logging
import re
from typing import override

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from unique_toolkit.agentic.postprocessor.postprocessor_manager import (
    ResponsesApiPostprocessor,
)
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.language_model.schemas import ResponsesLanguageModelStreamResponse

logger = logging.getLogger(__name__)


class ShowExecutedCodePostprocessorConfig(BaseModel):
    model_config = get_configuration_dict()
    remove_from_history: SkipJsonSchema[bool] = (
        Field(  # At the moment, it's not possible to keep executed code in the history
            default=True,
            description="If set, the code interpreter call will be removed from the history on subsequent calls to the assistant.",
        )
    )


class ShowExecutedCodePostprocessor(ResponsesApiPostprocessor):
    """Strips legacy `<details>` code blocks from the stored conversation history.

    Executed code used to be prepended to the assistant message as a
    `<details><summary>Code Interpreter Call</summary>` block. Since UN-25450 the
    code travels inside each `codeExecution` fence instead, so nothing is
    prepended any more. Messages written before that change still hold the old
    block, so it is removed here before the history goes back to the model.
    """

    def __init__(self, config: ShowExecutedCodePostprocessorConfig):
        super().__init__(self.__class__.__name__)
        self._config = config

    # `remove_from_text` does all the work, but the manager still calls `run` and
    # `apply_postprocessing_to_response` on every turn and the base class raises
    # NotImplementedError. So both must stay, even though they do nothing.
    @override
    async def run(self, loop_response: ResponsesLanguageModelStreamResponse) -> None:
        return None

    @override
    def apply_postprocessing_to_response(
        self, loop_response: ResponsesLanguageModelStreamResponse
    ) -> bool:
        return False

    @override
    async def remove_from_text(self, text) -> str:
        if not self._config.remove_from_history:
            return text
        pattern = r"<details><summary>Code Interpreter Call</summary>.*?</details>"
        return re.sub(pattern, "", text, flags=re.DOTALL)
