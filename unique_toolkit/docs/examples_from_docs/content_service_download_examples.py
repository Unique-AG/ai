import io

# %%
import os
import tempfile
from pathlib import Path

from unique_toolkit import ContentService, EmbeddingService, LanguageModelService
from unique_toolkit.app.init_sdk import init_unique_sdk
from unique_toolkit.app.unique_settings import UniqueSettings

settings = UniqueSettings.from_env(env_file=Path("../.env"))

init_unique_sdk(unique_settings=settings)

content_service = ContentService.from_settings(settings=settings)
llm_service = LanguageModelService.from_settings(settings=settings)
embedding_service = EmbeddingService.from_settings(settings=settings)

# Your application logic here
# Load configuration from environment variables
scope_id = os.getenv("UNIQUE_SCOPE_ID")
scope_ids = (
    os.getenv("UNIQUE_SCOPE_IDS", "").split(",")
    if os.getenv("UNIQUE_SCOPE_IDS")
    else None
)
content_id = os.getenv("UNIQUE_CONTENT_ID")
content_ids = (
    os.getenv("UNIQUE_CONTENT_IDS", "").split(",")
    if os.getenv("UNIQUE_CONTENT_IDS")
    else None
)
chat_id = os.getenv("UNIQUE_CHAT_ID")

# Fixed configuration values
file_path = "/path/to/document.pdf"
filename = "secure-document.pdf"
chunk_size = 1000
chunk_overlap = 200
reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
# Download content as bytes
content_bytes = content_service.download_content_to_bytes(
    content_id=content_id, chat_id=chat_id
)

# Process in memory
with io.BytesIO(content_bytes) as file_like:
    # Process the content without saving to disk
    pass
# Download to secure temporary file
temp_file_path = content_service.download_content_to_file_by_id(
    content_id=content_id,
    chat_id=chat_id,
    filename=filename,
    tmp_dir_path=tempfile.mkdtemp(),  # Use secure temp directory
)

try:
    # Process the file
    with open(temp_file_path, "rb") as file:
        # Your file processing logic here
        pass
finally:
    # Always clean up temporary files
    if temp_file_path.exists():
        temp_file_path.unlink()
    # Clean up the temporary directory
    temp_file_path.parent.rmdir()
response = content_service.request_content_by_id(content_id=content_id, chat_id=chat_id)

if response.status_code == 200:
    # Stream the content
    for chunk in response.iter_content(chunk_size=8192):
        # Process chunk by chunk
        pass
