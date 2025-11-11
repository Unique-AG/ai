import asyncio
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

_TEMPLATE = """
<details><summary>Code Interpreter Call</summary>    

```python
{code}
```  

</details>    
</br>

""".lstrip()

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
    def __init__(self, config: ShowExecutedCodePostprocessorConfig):
        super().__init__(self.__class__.__name__)
        self._config = config

    @override
    async def run(self, loop_response: ResponsesLanguageModelStreamResponse) -> None:
        await asyncio.sleep(self._config.sleep_time_before_display)

    @override
    def apply_postprocessing_to_response(
        self, loop_response: ResponsesLanguageModelStreamResponse
    ) -> bool:
        prepended_text = ""
        for output in loop_response.code_interpreter_calls:
            prepended_text += _TEMPLATE.format(code=output.code)

        loop_response.message.text = prepended_text + loop_response.message.text

        return prepended_text != ""

    @override
    async def remove_from_text(self, text) -> str:
        if not self._config.remove_from_history:
            return text
        # Remove code interpreter blocks using regex
        pattern = r"<details><summary>Code Interpreter Call</summary>.*?</details>"
        return re.sub(pattern, "", text, flags=re.DOTALL)
