# %%
import os
from pathlib import Path

import unique_sdk

MISSING
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
content_bytes = b"Your file content here"
content = content_service.upload_content_from_bytes(
    content=content_bytes,
    content_name="document.txt",
    mime_type="application/pdf",
    scope_id=scope_id,
    chat_id=chat_id,
    metadata={"category": "documentation", "version": "1.0"},
)
# Configure ingestion settings
ingestion_config = unique_sdk.Content.IngestionConfig(
    chunk_size=chunk_size, chunk_overlap=chunk_overlap, extract_images=True
)

content = content_service.upload_content(
    path_to_content=file_path,
    content_name=Path(file_path).name,
    mime_type="application/pdf",
    scope_id=scope_id,
    skip_ingestion=False,  # Process the content for search
    ingestion_config=ingestion_config,
    metadata={"department": "legal", "classification": "confidential"},
)
