# ruff: noqa: E402
import argparse
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import dotenv

dotenv.load_dotenv(os.getenv("UNIQUE_ENV_PATH"))

from langchain_core.messages import HumanMessage
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.service import ContentService
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.language_model import LanguageModelName
from unique_toolkit.language_model.infos import LanguageModelInfo

from unique_deep_research.config import UniqueEngine
from unique_deep_research.markdown_utils import validate_and_map_citations
from unique_deep_research.unique_custom.agents import custom_agent
from unique_deep_research.unique_custom.citation import GlobalCitationManager

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# CONFIG
INPUT_FILE = "deep_research_bench/data/prompt_data/query.jsonl"
OUTPUT_FILE = (
    "deep_research_bench/data/test_data/raw_data/unique-custom-gpt-5-2025-0807.jsonl"
)
base_dir = Path(__file__).parent
input_file = base_dir / INPUT_FILE
output_file = base_dir / OUTPUT_FILE
output_file.parent.mkdir(parents=True, exist_ok=True)


# Mock Services
class BenchmarkChatService(ChatService):
    """Minimal ChatService for benchmarking - passes isinstance() checks."""

    def __init__(self):
        # Skip parent init to avoid dependency requirements
        pass

    def create_message_log(self, **kwargs):
        """No-op: Benchmarking doesn't track progress logs."""
        pass


class BenchmarkContentService(ContentService):
    """Minimal ContentService for benchmarking - not used (internal tools disabled)."""

    def __init__(self):
        # Skip parent init
        pass

    async def search_content_chunks_async(self, **kwargs):
        """Not called when enable_internal_tools=False."""
        logger.warning("Internal tools called despite being disabled!")
        return []


# Singleton instances (reuse across all queries)
CHAT_SERVICE = BenchmarkChatService()
CONTENT_SERVICE = BenchmarkContentService()


# File I/O Helpers
def load_queries(path: Path) -> list[dict]:
    """Load queries from JSONL file."""
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def load_completed_ids(path: Path) -> set[int]:
    """Load completed query IDs from output file."""
    if not path.exists():
        return set()
    with open(path, encoding="utf-8") as f:
        return {json.loads(line)["id"] for line in f}


def save_result(path: Path, result: dict) -> None:
    """Append result to output JSONL file."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")


def log_progress(completed: int, total: int, elapsed_sec: float) -> None:
    """Log progress with ETA."""
    pct = completed / total * 100
    eta_hours = (total - completed) * (elapsed_sec / completed) / 3600
    logger.info(f"Progress: {completed}/{total} ({pct:.1f}%) | ETA: {eta_hours:.1f}h")
    logger.info("-" * 80)


# Core Research Functions
async def run_single_research(query: dict) -> dict:
    """
    Run deep research for a single benchmark query.

    Args:
        query: Dict with {id, topic, language, prompt}

    Returns:
        Dict with {id, prompt, article}
    """
    query_id = query["id"]
    prompt = query["prompt"]

    logger.info(f"[{query_id}/100] Starting: {prompt[:80]}...")
    start_time = datetime.now()

    try:
        # Setup services and config
        client = get_openai_client()
        citation_manager = GlobalCitationManager()
        engine_config = UniqueEngine(
            research_model=LanguageModelInfo.from_name(
                LanguageModelName.AZURE_GPT_5_2025_0807
            )
        )

        # Build initial state
        initial_state = {
            "messages": [HumanMessage(content=prompt)],
            "research_brief": prompt,  # Use raw query directly
            "notes": [],
            "final_report": "",
            "supervisor_messages": [],
            "research_iterations": 0,
            "chat_service": CHAT_SERVICE,
            "message_id": f"bench_{query_id}",
            "tool_progress_reporter": None,  # Optional field
        }

        # Build config with web-only tools
        config = {
            "configurable": {
                "engine_config": engine_config,
                "openai_client": client,
                "chat_service": CHAT_SERVICE,
                "content_service": CONTENT_SERVICE,
                "message_id": f"bench_{query_id}",
                "citation_manager": citation_manager,
                "enable_web_tools": True,  # Enable web search
                "enable_internal_tools": False,  # Disable internal tools
            },
        }

        # Run research
        logger.info(f"[{query_id}/100] Invoking custom_agent...")
        result = await custom_agent.ainvoke(initial_state, config=config)

        # Extract and validate
        final_report = result.get("final_report", "")
        if not final_report:
            logger.warning(f"[{query_id}/100] Empty final_report")
            return {"id": query_id, "prompt": prompt, "article": ""}

        # Process citations
        citation_registry = citation_manager.get_all_citations()
        processed_article, references = validate_and_map_citations(
            final_report, citation_registry
        )

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"[{query_id}/100] ✓ Completed in {elapsed:.1f}s ({len(references)} refs)"
        )

        return {
            "id": query_id,
            "prompt": prompt,
            "article": processed_article,
        }

    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.error(f"[{query_id}/100] ✗ Failed after {elapsed:.1f}s: {e}")
        return {
            "id": query_id,
            "prompt": prompt,
            "article": f"ERROR: {str(e)}",
        }


async def process_with_semaphore(
    query: dict, output_file: Path, semaphore: asyncio.Semaphore
) -> dict:
    """Process a single query with concurrency control and save result."""
    async with semaphore:
        result = await run_single_research(query)
        save_result(output_file, result)
        return result


async def main(max_concurrent: int = 1, limit: int | None = None):
    """
    Process all 100 benchmark queries with resume support and parallel execution.

    Args:
        max_concurrent: Maximum number of concurrent research tasks (default: 1 for sequential)
        limit: Maximum number of queries to process (None for all)
    """
    # Paths

    # Load queries and check what's already done
    queries = load_queries(input_file)
    completed_ids = load_completed_ids(output_file)
    logger.info(f"Loaded {len(queries)} queries, {len(completed_ids)} completed")

    # Filter uncompleted
    remaining = [q for q in queries if q["id"] not in completed_ids]

    # Apply limit if specified
    if limit is not None:
        remaining = remaining[:limit]
        logger.info(f"Limiting to first {limit} uncompleted queries")

    if not remaining:
        logger.info("✓ All queries already completed!")
        return

    logger.info("=" * 80)
    logger.info(f"Processing {len(remaining)} remaining queries")
    logger.info(f"Concurrency: {max_concurrent} parallel tasks")
    logger.info(
        f"⚠️  Estimated time: ~{12 / max_concurrent:.1f}-{17 / max_concurrent:.1f} hours | Cost: ~$200-500"
    )
    logger.info("=" * 80)

    # Process with concurrency control
    start_time = datetime.now()
    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = [process_with_semaphore(q, output_file, semaphore) for q in remaining]

    # Run with progress tracking
    completed = 0
    for coro in asyncio.as_completed(tasks):
        await coro
        completed += 1

        total_done = len(completed_ids) + completed
        elapsed = (datetime.now() - start_time).total_seconds()
        log_progress(total_done, len(queries), elapsed)

    total_time = (datetime.now() - start_time).total_seconds()
    logger.info("=" * 80)
    logger.info(f"✓ COMPLETE! Total time: {total_time / 3600:.1f}h")
    logger.info(f"Output: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run DeepResearch Bench on Unique Custom Agent"
    )
    parser.add_argument(
        "--concurrency",
        "-c",
        type=int,
        default=1,
        help="Maximum number of concurrent research tasks (default: 1 for sequential)",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="Limit number of queries to process (useful for testing)",
    )

    args = parser.parse_args()

    asyncio.run(main(max_concurrent=args.concurrency, limit=args.limit))
