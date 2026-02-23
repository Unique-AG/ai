import re

from unique_web_search.services.content_processing.cleaning.config import (
    LineRemovalPatternsConfig,
    MarkdownTransformationConfig,
)


class LineRemoval:
    def __init__(self, config: LineRemovalPatternsConfig):
        self.config = config

    def __call__(self, content: str) -> str:
        if self.config.enabled:
            lines = content.split("\n")

            filtered_lines = []
            for line in lines:
                skip = True
                for pattern in self.config.patterns:
                    if re.search(pattern, line, flags=re.IGNORECASE):
                        skip = False
                        break
                if skip:
                    filtered_lines.append(line)
            content = "\n".join(filtered_lines)
        return content

    @property
    def is_enabled(self) -> bool:
        return self.config.enabled


class MarkdownTransform:
    def __init__(self, config: MarkdownTransformationConfig):
        self.config = config

    def __call__(self, content: str) -> str:
        if self.config.enabled:
            for transformation in self.config.transformations.root:
                content = re.sub(transformation.source, transformation.target, content)
        return content

    @property
    def is_enabled(self) -> bool:
        return self.config.enabled
