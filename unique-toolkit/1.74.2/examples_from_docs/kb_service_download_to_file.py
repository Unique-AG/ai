# %%
import tempfile
from pathlib import Path

from dotenv import dotenv_values

from unique_toolkit import (
    KnowledgeBaseService,
)

kb_service = KnowledgeBaseService.from_settings()
demo_env_vars = dotenv_values(Path(__file__).parent / "demo.env")
content_id = demo_env_vars.get("UNIQUE_CONTENT_ID") or "unknown"
# Download to secure temporary file

filename = "my_testfile.txt"
temp_file_path = kb_service.download_content_to_file(
    content_id=content_id,
    output_filename=filename,
    output_dir_path=Path(tempfile.mkdtemp()),  # Use secure temp directory
)

try:
    # Process the file
    with open(temp_file_path, "rb") as file:
        text = file.read().decode("utf-8")
        print(text)
finally:
    # Always clean up temporary files
    if temp_file_path.exists():
        temp_file_path.unlink()
    # Clean up the temporary directory
    temp_file_path.parent.rmdir()
