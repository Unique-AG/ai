"""
Example: Using the Write-Up Agent to generate summaries from DataFrame data.
"""

# TODO [UN-16142]: Add example usage in tutorial instead of here

import logging
from pathlib import Path

import pandas as pd

from unique_toolkit._common.experimental.write_up_agent import (
    WriteUpAgent,
    WriteUpAgentConfig,
)
from unique_toolkit._common.experimental.write_up_agent.services.generation_handler.config import (
    GenerationHandlerConfig,
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
    generation_handler_config=GenerationHandlerConfig(
        # Optional: Customize generation settings
        # max_rows_per_batch=20,  # Max rows per batch (default: 20)
        # max_tokens_per_batch=4000,  # Max tokens per batch (default: 4000)
        # common_instruction="You are a technical writer...",  # Custom system prompt
        # group_specific_instructions={
        #     # IMPORTANT: Both column and value must be in snake_case
        #     # DataFrame: Section="Introduction" → Key: "section:introduction"
        #     "section:introduction": "Be welcoming and engaging",
        #     "section:methods": "Be precise and technical"
        # }
    )
)

# Initialize the agent with LLM service
write_up_agent = WriteUpAgent(
    config=write_up_agent_config,
)

# Load your DataFrame
# IMPORTANT: DataFrame must have columns: section, question, answer (otherwise adapt the template)
df = pd.read_csv(data_path)

print(f"Processing {len(df)} rows across {df['section'].nunique()} sections...")
print(f"Columns in DataFrame: {list(df.columns)}")
print()

llm_service = LanguageModelService.from_settings(_SETTINGS)

# Generate the report
report = write_up_agent.process(df, llm_service=llm_service)

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
