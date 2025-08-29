# ~/~ begin <<docs/modules/examples/content/content_service.md#docs/.python_files/content_service_download_examples.py>>[init]
# ~/~ begin <<docs/modules/examples/content/content_service.md#content_service_setup>>[init]
# ~/~ begin <<docs/modules/examples/content/content_service.md#content_service_imports>>[init]
import os
import io
import tempfile
import requests
from pathlib import Path
from unique_toolkit.content.schemas import ContentSearchType, ContentRerankerConfig
import unique_sdk
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/content_service.md#initialize_content_service_standalone>>[init]
MISSING
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/content_service.md#content_service_config>>[init]
# Load configuration from environment variables
scope_id = os.getenv("UNIQUE_SCOPE_ID")
scope_ids = os.getenv("UNIQUE_SCOPE_IDS", "").split(",") if os.getenv("UNIQUE_SCOPE_IDS") else None
content_id = os.getenv("UNIQUE_CONTENT_ID")
content_ids = os.getenv("UNIQUE_CONTENT_IDS", "").split(",") if os.getenv("UNIQUE_CONTENT_IDS") else None
chat_id = os.getenv("UNIQUE_CHAT_ID")

# Fixed configuration values
file_path = "/path/to/document.pdf"
filename = "secure-document.pdf"
chunk_size = 1000
chunk_overlap = 200
reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
# ~/~ end
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/content_service.md#content_service_download_bytes>>[init]
# Download content as bytes
content_bytes = content_service.download_content_to_bytes(
    content_id=content_id,
    chat_id=chat_id
)

# Process in memory
with io.BytesIO(content_bytes) as file_like:
    # Process the content without saving to disk
    pass
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/content_service.md#content_service_download_file>>[init]
# Download to secure temporary file
temp_file_path = content_service.download_content_to_file_by_id(
    content_id=content_id,
    chat_id=chat_id,
    filename=filename,
    tmp_dir_path=tempfile.mkdtemp()  # Use secure temp directory
)

try:
    # Process the file
    with open(temp_file_path, 'rb') as file:
        # Your file processing logic here
        pass
finally:
    # Always clean up temporary files
    if temp_file_path.exists():
        temp_file_path.unlink()
    # Clean up the temporary directory
    temp_file_path.parent.rmdir()
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/content_service.md#content_service_request_content>>[init]
response = content_service.request_content_by_id(
    content_id=content_id,
    chat_id=chat_id
)

if response.status_code == 200:
    # Stream the content
    for chunk in response.iter_content(chunk_size=8192):
        # Process chunk by chunk
        pass
# ~/~ end
# ~/~ end
