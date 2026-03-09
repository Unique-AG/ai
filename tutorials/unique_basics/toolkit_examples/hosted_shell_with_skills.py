# %%
"""
Hosted Shell with Skills — Tutorial
====================================

Demonstrates using the OpenAI Hosted Shell tool with two types of skills:

1. **Skill references** (curated/uploaded) — e.g. ``openai-spreadsheets``
2. **Inline skills** (embedded in the request) — custom behaviour via a SKILL.md

The example uploads a CSV file, uses the shell to analyse it,
and streams the response with reasoning/thinking tokens.

Prerequisites:
    - ``OPENAI_API_KEY`` environment variable (or in ``.env``)
    - ``pip install unique-toolkit openai python-dotenv``
"""

import base64
import io
import zipfile
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from unique_toolkit.agentic.tools.openai_builtin.hosted_shell.config import (
    InlineSkillConfig,
    OpenAIHostedShellConfig,
    SkillReferenceConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.hosted_shell.service import (
    OpenAIHostedShellTool,
)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = OpenAI()

# %%
# ── 1. Upload a sample file ────────────────────────────────────────
# In a real scenario you would point this to your own file.
# Here we create a small CSV in-memory for demonstration.

SAMPLE_CSV = (
    "Name,Department,Score\n"
    "Alice,Engineering,92\n"
    "Bob,Marketing,78\n"
    "Carol,Engineering,88\n"
    "Dave,Marketing,65\n"
    "Eve,Sales,95\n"
)

csv_bytes = SAMPLE_CSV.encode()
uploaded = client.files.create(file=("scores.csv", csv_bytes), purpose="assistants")
print(f"Uploaded file: {uploaded.id}")

# %%
# ── 2. Build an inline skill ───────────────────────────────────────
# Inline skills let you embed custom instructions as a base64-encoded
# zip containing a SKILL.md file. The model follows these instructions
# when using the hosted shell.

SKILL_NAME = "chart-creator"
SKILL_DESCRIPTION = "Creates bar charts from tabular data using matplotlib"

skill_md = f"""\
---
name: {SKILL_NAME}
description: {SKILL_DESCRIPTION}
---

## Instructions

When asked to visualise tabular data, create a bar chart using matplotlib:

1. Read the data with pandas
2. Create a bar chart with clear labels and a title
3. Save the chart as a PNG file

### Example code

```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("data.csv")
df.plot(kind="bar", x="Name", y="Score", title="Scores by Person")
plt.tight_layout()
plt.savefig("chart.png", dpi=150)
print("Chart saved to chart.png")
```
"""

# Package the skill as a zip archive (required format)
zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.writestr(f"{SKILL_NAME}/SKILL.md", skill_md)
b64_zip = base64.b64encode(zip_buffer.getvalue()).decode()

print(f"Built inline skill '{SKILL_NAME}' ({len(zip_buffer.getvalue())} bytes)")

# %%
# ── 3. Configure the hosted shell tool ─────────────────────────────
# Combines a curated skill reference with the inline skill above.

config = OpenAIHostedShellConfig(
    use_auto_container=True,
    skill_references=[
        SkillReferenceConfig(
            skill_id="openai-spreadsheets",
            version="latest",
        ),
    ],
    inline_skills=[
        InlineSkillConfig(
            name=SKILL_NAME,
            description=SKILL_DESCRIPTION,
            base64_zip=b64_zip,
        ),
    ],
)

tool = OpenAIHostedShellTool(
    config=config,
    container_id=None,
    file_ids=[uploaded.id],
)

tool_desc = tool.tool_description()
print(f"Tool type: {tool_desc['type']}")

# %%
# ── 4. Stream the response with reasoning ──────────────────────────

print("\nRunning analysis with streaming + reasoning...\n")

stream = client.responses.create(
    model="o3",
    tools=[tool_desc],
    instructions=(
        "You have access to the openai-spreadsheets and chart-creator skills. "
        "Read the uploaded CSV file 'scores.csv' from /mnt/user. "
        "Compute the average score per department. "
        "Then use the chart-creator skill to create a bar chart of average "
        "scores by department. Save the chart to /mnt/user/department_scores.png."
    ),
    input="Analyse scores.csv: compute department averages and create a chart.",
    reasoning={"effort": "high", "summary": "auto"},
    include=["reasoning.encrypted_content"],
    stream=True,
)

# ── 5. Process streaming events ────────────────────────────────────

for event in stream:
    if event.type == "response.reasoning_summary_text.delta":
        print(f"[thinking] {event.delta}", end="", flush=True)

    elif event.type == "response.reasoning_summary_text.done":
        print()

    elif event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)

    elif event.type == "response.output_text.done":
        print()

    elif event.type == "response.completed":
        response = event.response

print("\n--- Done ---")

# %%
# ── 6. Download generated files ────────────────────────────────────
# Files produced by the shell can be found via annotations on the
# response output, or by listing container files directly.

for item in response.output:
    if not hasattr(item, "content") or not item.content:
        continue
    for content_block in item.content:
        if not hasattr(content_block, "annotations"):
            continue
        for ann in content_block.annotations or []:
            if hasattr(ann, "container_id") and hasattr(ann, "file_id"):
                print(f"Generated file: {ann.filename}")
                file_data = client.containers.files.content.retrieve(
                    container_id=ann.container_id,
                    file_id=ann.file_id,
                )
                output_path = Path(__file__).parent / ann.filename
                output_path.write_bytes(file_data.content)
                print(f"Saved to: {output_path}")
