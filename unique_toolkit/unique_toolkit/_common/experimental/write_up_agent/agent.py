"""
Write-Up Agent - Main pipeline orchestrator.
"""

import logging

import pandas as pd

from unique_toolkit._common.experimental.write_up_agent.config import (
    WriteUpAgentConfig,
)
from unique_toolkit._common.experimental.write_up_agent.services.dataframe_handler import (
    DataFrameHandler,
)
from unique_toolkit._common.experimental.write_up_agent.services.dataframe_handler.exceptions import (
    DataFrameGroupingError,
    DataFrameHandlerError,
    DataFrameProcessingError,
    DataFrameValidationError,
)
from unique_toolkit._common.experimental.write_up_agent.services.generation_handler import (
    GenerationHandler,
    GenerationHandlerError,
)
from unique_toolkit._common.experimental.write_up_agent.services.template_handler import (
    TemplateHandler,
)
from unique_toolkit._common.experimental.write_up_agent.services.template_handler.exceptions import (
    ColumnExtractionError,
    TemplateHandlerError,
    TemplateParsingError,
    TemplateRenderingError,
    TemplateStructureError,
)
from unique_toolkit.language_model.service import LanguageModelService

_LOGGER = logging.getLogger(__name__)


class WriteUpAgent:
    """
    Main pipeline orchestrator for DataFrame summarization.

    Orchestrates the complete pipeline:
    1. Extract template info (grouping + columns)
    2. Validate DataFrame
    3. Create groups
    4. Render each group
    5. Process with LLM
    6. Return results
    """

    def __init__(self, config: WriteUpAgentConfig, llm_service: LanguageModelService):
        """
        Initialize WriteUpAgent.

        Args:
            config: Configuration with template and settings
        """
        self._config = config
        self.template_handler = TemplateHandler(config.template)
        self.dataframe_handler = DataFrameHandler()

        # Create generation handler with injected renderer
        def renderer(group_data, llm_response=None):
            return self.template_handler.render_group(group_data, llm_response)

        self.generation_handler = GenerationHandler(
            self._config.generation_handler_config, llm_service, renderer
        )

    def process(self, df: pd.DataFrame) -> str:
        """
        Execute complete pipeline and generate final report.

        Args:
            df: pandas DataFrame to process

        Returns:
            Final markdown report as a single string with all groups processed

        Raises:
            Various handler exceptions if processing fails

        Example:
            >>> config = WriteUpAgentConfig(template="...", max_rows_per_group=10)
            >>> agent = WriteUpAgent(config)
            >>> report = agent.process(df)
            >>> print(report)
        """
        try:
            # Step 1: Extract template structure
            _LOGGER.info("Extracting template structure...")
            grouping_column = self.template_handler.get_grouping_column()
            selected_columns = self.template_handler.get_selected_columns()
            _LOGGER.info(f"Detected grouping column: {grouping_column}")
            _LOGGER.info(f"Detected data columns: {selected_columns}")

            # Step 2: Validate DataFrame
            _LOGGER.info("Validating DataFrame columns...")
            self.dataframe_handler.validate_columns(
                df, grouping_column, selected_columns
            )

            # Step 3: Create groups
            _LOGGER.info("Creating groups from DataFrame...")
            groups = self.dataframe_handler.create_groups(
                df, grouping_column, selected_columns
            )
            _LOGGER.info(f"Created {len(groups)} groups")

            # Step 4: Process groups with GenerationHandler
            _LOGGER.info("Processing groups with GenerationHandler...")
            processed_groups = self.generation_handler.process_groups(
                groups, grouping_column
            )
            _LOGGER.info(f"Generation complete for {len(processed_groups)} groups")

            # Step 5: Render final report with LLM responses
            _LOGGER.info("Rendering final report...")

            final_report = self.template_handler.render_all_groups(processed_groups)

            _LOGGER.info(f"Report generated ({len(final_report)} characters)")

            return final_report

        except TemplateParsingError as e:
            _LOGGER.error(f"Template parsing failed: {e}")
            raise

        except TemplateStructureError as e:
            _LOGGER.error(f"Template structure invalid: {e}")
            raise

        except ColumnExtractionError as e:
            _LOGGER.error(f"Column extraction failed: {e}")
            raise

        except DataFrameValidationError as e:
            _LOGGER.error(f"DataFrame validation failed: {e}")
            raise

        except DataFrameGroupingError as e:
            _LOGGER.error(f"DataFrame grouping failed: {e}")
            raise

        except DataFrameProcessingError as e:
            _LOGGER.error(f"DataFrame processing failed: {e}")
            raise

        except GenerationHandlerError as e:
            _LOGGER.error(f"Generation failed: {e}")
            raise

        except TemplateRenderingError as e:
            _LOGGER.error(f"Final rendering failed: {e}")
            raise

        except (TemplateHandlerError, DataFrameHandlerError) as e:
            _LOGGER.error(f"Handler error: {e}")
            raise

        except Exception as e:
            _LOGGER.error(f"Unexpected error: {e}", exc_info=True)
            raise
