# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "unique-toolkit>=2026.22.0",
#   "unique-sdk>=2026.22.0",
# ]
# ///


from unique_toolkit import (
    KnowledgeBaseService,
)
from unique_toolkit.framework_utilities.openai.client import get_openai_client

kb_service = KnowledgeBaseService.from_settings()
client = get_openai_client()
