"""Click entry point for the unique-websearch CLI."""

from __future__ import annotations

import sys

import click

from unique_web_search.cli import __version__
from unique_web_search.cli.cli_config import (
    CLIConfigError,
    load_websearch_config,
)
from unique_web_search.cli.commands.websearch import cmd_websearch

HELP_TEXT = """\
Search the web from your terminal using the configured search engine.

QUERY is the text to search for. The search engine and crawler are
determined by environment variables (ACTIVE_SEARCH_ENGINES and
ACTIVE_INHOUSE_CRAWLERS), matching the server-side configuration.
An optional JSON config file can override non-secret settings like
fetch_size.

\b
Environment variables (search engine selection):
  ACTIVE_SEARCH_ENGINES       Which engine to use (default: google)
  ACTIVE_INHOUSE_CRAWLERS     Which crawlers are available (default: basic, crawl4ai)

\b
Environment variables (API keys, set for your configured engine):
  Google:    GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_ENGINE_ID, GOOGLE_SEARCH_API_ENDPOINT
  Brave:     BRAVE_SEARCH_API_KEY, BRAVE_SEARCH_API_ENDPOINT
  Tavily:    TAVILY_API_KEY
  Jina:      JINA_API_KEY
  Firecrawl: FIRECRAWL_API_KEY

\b
Optional config file (~/.unique-websearch.json):
  Override non-secret settings like fetch_size. Engine and crawler
  selection still comes from environment variables.

  {
    "search_engine_config": { "fetch_size": 50 },
    "crawler_config": { "timeout": 10 }
  }

\b
Examples:
  unique-websearch "quarterly earnings 2025"
  unique-websearch "AI regulation" -n 10
  unique-websearch "python tutorial" --no-crawl
  unique-websearch "internal docs" --config ./project.json
"""


@click.command(help=HELP_TEXT)
@click.argument("query")
@click.option(
    "--fetch-size",
    "-n",
    default=None,
    type=int,
    help="Number of results to fetch (default: 50, or from config).",
)
@click.option(
    "--no-crawl",
    is_flag=True,
    help="Skip page crawling, show URLs and snippets only.",
)
@click.option(
    "--config",
    "-c",
    "config_path",
    default=None,
    type=click.Path(),
    help="Path to JSON config file (default: ~/.unique-websearch.json).",
)
@click.version_option(version=__version__, prog_name="unique-websearch")
def main(
    query: str,
    fetch_size: int | None,
    no_crawl: bool,
    config_path: str | None,
) -> None:
    try:
        search_engine_config, crawler_config = load_websearch_config(
            config_path=config_path,
        )
    except CLIConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    result = cmd_websearch(
        search_engine_config=search_engine_config,
        crawler_config=crawler_config,
        query=query,
        fetch_size=fetch_size,
        no_crawl=no_crawl,
    )
    click.echo(result)
