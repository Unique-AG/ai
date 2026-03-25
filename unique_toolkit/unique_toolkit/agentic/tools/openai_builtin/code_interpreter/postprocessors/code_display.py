import asyncio
import logging
import re
from typing import override

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from unique_toolkit.agentic.feature_flags.feature_flags import feature_flags
from unique_toolkit.agentic.postprocessor.postprocessor_manager import (
    ResponsesApiPostprocessor,
)
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.language_model.schemas import ResponsesLanguageModelStreamResponse

_TEMPLATE = """
<details><summary>Code Interpreter Call</summary>    

```python
{code}
```  

</details>    
</br>

""".lstrip()

# Pattern matching the block emitted by _TEMPLATE (including trailing </br>).
# Used by remove_from_text to clean history entries.
_EXECUTED_CODE_BLOCK_RE = re.compile(
    r"\n*<details><summary>Code Interpreter Call</summary>.*?</details>[ \t]*\n*(?:[ \t]*</br>[ \t]*\n*)?",
    re.DOTALL,
)


logger = logging.getLogger(__name__)


class ShowExecutedCodePostprocessorConfig(BaseModel):
    model_config = get_configuration_dict()
    remove_from_history: SkipJsonSchema[bool] = (
        Field(  # At the moment, it's not possible to keep executed code in the history
            default=True,
            description="If set, the code interpreter call will be removed from the history on subsequent calls to the assistant.",
        )
    )
    sleep_time_before_display: float = Field(
        default=0.2,
        description="Time to sleep before displaying the executed code. Please increase this value if you experience rendering issues.",
    )


class ShowExecutedCodePostprocessor(ResponsesApiPostprocessor):
    def __init__(
        self,
        config: ShowExecutedCodePostprocessorConfig,
        company_id: str | None = None,
    ):
        super().__init__(self.__class__.__name__)
        self._config = config
        self._company_id = company_id

    @override
    async def run(self, loop_response: ResponsesLanguageModelStreamResponse) -> None:
        if feature_flags.enable_code_execution_fence_un_17972.is_enabled(
            self._company_id
        ):
            return
        await asyncio.sleep(self._config.sleep_time_before_display)

    @override
    def apply_postprocessing_to_response(
        self, loop_response: ResponsesLanguageModelStreamResponse
    ) -> bool:
        if feature_flags.enable_code_execution_fence_un_17972.is_enabled(
            self._company_id
        ):
            return False

        prepended_text = ""
        for output in loop_response.code_interpreter_calls:
            prepended_text += _TEMPLATE.format(code=output.code)

        loop_response.message.text = prepended_text + loop_response.message.text

        return prepended_text != ""

    @override
    async def remove_from_text(self, text) -> str:
        if not self._config.remove_from_history:
            return text
        pattern = r"<details><summary>Code Interpreter Call</summary>.*?</details>"
        return re.sub(pattern, "", text, flags=re.DOTALL)
