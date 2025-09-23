from mimetypes import guess_type
import re
from typing import override

from openai import AsyncOpenAI
from openai.types.responses.response_output_text import AnnotationContainerFileCitation
from pydantic import BaseModel
from unique_toolkit.agentic.postprocessor.postprocessor_manager import Postprocessor
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model.schemas import ResponsesLanguageModelStreamResponse

_TEMPLATE = """
<details><summary>Code Interpreter Call</summary>    

```python
{code}
```  

</details>    
</br>

""".lstrip()


class ShowInterpreterCodePostprocessor(
    Postprocessor[ResponsesLanguageModelStreamResponse]
):
    def __init__(self):
        super().__init__(self.__class__.__name__)

    @override
    async def run(self, loop_response: ResponsesLanguageModelStreamResponse) -> str:
        return ""

    @override
    async def apply_postprocessing_to_response(
        self, loop_response: ResponsesLanguageModelStreamResponse
    ) -> bool:
        prepended_text = ""
        for output in loop_response.output:
            if output.type == "code_interpreter_call":
                prepended_text += _TEMPLATE.format(code=output.code)

        loop_response.message.text = prepended_text + loop_response.message.text

        return prepended_text != ""

    @override
    async def remove_from_text(self, text) -> str:
        # Remove code interpreter blocks using regex
        pattern = r"<details><summary>Code Interpreter Call</summary>.*?</details>"
        return re.sub(pattern, "", text, flags=re.DOTALL)


class DisplayCodeInterpreterFilesPostProcessorConfig(BaseModel):
    model_config = get_configuration_dict()
    upload_scope_id: str


class DisplayCodeInterpreterFilesPostProcessor(
    Postprocessor[ResponsesLanguageModelStreamResponse]
):
    def __init__(
        self,
        client: AsyncOpenAI,
        content_service: ContentService,
        config: DisplayCodeInterpreterFilesPostProcessorConfig,
    ) -> None:
        super().__init__(self.__class__.__name__)
        self._content_service = content_service
        self._config = config
        self._client = client
        self._content_map = {}

    @override
    async def run(self, loop_response: ResponsesLanguageModelStreamResponse) -> str:
        container_files: list[AnnotationContainerFileCitation] = []
        for output in loop_response.output:
            if output.type == "message":
                for content in output.content:
                    if content.type == "output_text":
                        for annotation in content.annotations:
                            if annotation.type == "container_file_citation":
                                container_files.append(annotation)

        self._content_map = {}
        for container_file in container_files:
            file_content = await self._client.containers.files.content.retrieve(
                container_id=container_file.container_id, file_id=container_file.file_id
            )
            content = self._content_service.upload_content_from_bytes(
                content=file_content.content,
                content_name=container_file.filename,
                skip_ingestion=True,
                mime_type=guess_type(container_file.filename)[0] or "text/plain",
                scope_id=self._config.upload_scope_id,
            )
            self._content_map[container_file.filename] = content
        return ""

    @override
    async def apply_postprocessing_to_response(
        self, loop_response: ResponsesLanguageModelStreamResponse
    ) -> bool:
        # images
        for filename, content in self._content_map.items():
            image_markdown = rf"!\[.*?\]\(sandbox:/mnt/data/{re.escape(filename)}\)"
            loop_response.message.text = re.sub(
                image_markdown,
                f"![image](unique://content/{content.id})",
                loop_response.message.text,
            )
        return True

    @override
    async def remove_from_text(self, text) -> str:
        return text
