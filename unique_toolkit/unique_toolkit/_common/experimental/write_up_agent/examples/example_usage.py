"""
Example: Using the Write-Up Agent to generate summaries from DataFrame data.

This example demonstrates:
1. Setting up the Write-Up Agent with default configuration
2. Processing a DataFrame to generate a structured markdown report
3. Understanding the default template requirements

DEFAULT TEMPLATE REQUIREMENTS:
------------------------------
The default template expects a DataFrame with these columns:
- 'section': The grouping column (e.g., "Introduction", "Methods", "Results")
- 'question': The question text (referenced in the template)
- 'answer': The answer text (referenced in the template)

The template groups rows by 'section' and generates a summary for each section's Q&A pairs.

IMPORTANT - COLUMN NAME NORMALIZATION:
--------------------------------------
The agent automatically converts ALL column names to snake_case for Jinja template compatibility.

Examples of automatic conversion:
- "My Column" → "my_column"
- "UserName" → "user_name"
- "Section Name" → "section_name"
- "column-name" → "column_name"

This means:
✓ Your DataFrame can have ANY column name format (spaces, PascalCase, kebab-case, etc.)
✓ Your template MUST use snake_case references (e.g., {{ row.my_column }})
✓ The default template expects: section, question, answer (all lowercase, snake_case)

EXAMPLE CSV STRUCTURE:
----------------------
section,question,answer
Introduction,What is this project about?,This is a data analysis project...
Introduction,Who is the target audience?,Data scientists and researchers...
Methods,What tools were used?,We used Python and pandas...
Methods,How was the data collected?,Data was collected via surveys...

OR with different column names (will be auto-converted to snake_case):
"My Section","User Question","User Answer"
Introduction,What is this?,A project...
Methods,How?,We used Python...

The agent will:
1. Normalize column names to snake_case
2. Group rows by 'section'
3. For each section, render Q&A pairs as input for the LLM
4. Generate a summary for each section
5. Combine all sections into a final markdown report
"""

import logging
from pathlib import Path

import pandas as pd

from unique_toolkit._common.experimental.write_up_agent import (
    WriteUpAgent,
    WriteUpAgentConfig,
)
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.language_model.service import LanguageModelService

logging.basicConfig(level=logging.DEBUG)

# Setup paths
current_dir = Path(__file__).parent
env_path = current_dir / "unique.env"
data_path = current_dir / "data.csv"

# Initialize SDK with your API keys
_SETTINGS = UniqueSettings.from_env(env_file=env_path)
_SETTINGS.init_sdk()

# Configure the Write-Up Agent
# Using default configuration which expects: section, question, answer columns
write_up_agent_config = WriteUpAgentConfig(
    # Optional: Customize generation settings
    # max_rows_per_group=20,  # Max rows per batch (default: 20)
    # max_tokens_per_group=4000,  # Max tokens per batch (default: None)
    # common_instruction="You are a technical writer...",  # Custom system prompt
    # group_specific_instructions={
    #     "section:Introduction": "Be welcoming and engaging",
    #     "section:Methods": "Be precise and technical"
    # }
)

# Initialize the agent with LLM service
write_up_agent = WriteUpAgent(
    config=write_up_agent_config,
    llm_service=LanguageModelService.from_settings(_SETTINGS),
)

# Load your DataFrame
# IMPORTANT: DataFrame must have columns: section, question, answer
df = pd.read_csv(data_path)

print(f"Processing {len(df)} rows across {df['section'].nunique()} sections...")
print(f"Columns in DataFrame: {list(df.columns)}")
print()

# Generate the report
report = write_up_agent.process(df)

# Display the result
print("=" * 80)
print("GENERATED REPORT")
print("=" * 80)
print(report)

# Optional: Save to file
output_path = current_dir / "report.md"
output_path.write_text(report)
print()
print(f"Report saved to: {output_path}")
