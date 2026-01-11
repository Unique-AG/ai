"""
Write-Up Agent: Template-driven DataFrame summarization and report generation.
"""

from unique_toolkit._common.experimental.write_up_agent.agent import WriteUpAgent
from unique_toolkit._common.experimental.write_up_agent.config import (
    WriteUpAgentConfig,
)
from unique_toolkit._common.experimental.write_up_agent.schemas import (
    GroupData,
    ProcessedGroup,
)

__all__ = [
    # Main agent
    "WriteUpAgent",
    # Configuration
    "WriteUpAgentConfig",
    # Data schemas
    "GroupData",
    "ProcessedGroup",
]
