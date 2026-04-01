"""Click entry point for the unique-websearch CLI."""

from __future__ import annotations

import sys

import click

from unique_web_search.cli import __version__
from unique_web_search.cli.cli_config import (
    SUPPORTED_CRAWLERS,
    SUPPORTED_ENGINES,
    CLIConfigError,
    load_websearch_config,
)
from unique_web_search.cli.commands.websearch import cmd_websearch

HELP_TEXT = (
    """\
Search the web from your terminal using configurable search engines.

QUERY is the text to search for. Results are fetched from the search
engine configured in your JSON config file, and optionally crawled
to retrieve full page content.

\b
Config file (required):
  ~/.unique-websearch.json   Default location
  UNIQUE_WEBSEARCH_CONFIG    Env var to override path
  --config / -c PATH         CLI flag to override path

\b
Config file format:
  {
    "search_engine_config": {
      "search_engine_name": "Google",
      "fetch_size": 5
    },
    "crawler_config": {
      "crawler_type": "BasicCrawler",
      "timeout": 10
    }
  }

\b
Supported search engines:  """
    + ", ".join(SUPPORTED_ENGINES)
    + """
Supported crawlers:        """
    + ", ".join(SUPPORTED_CRAWLERS)
    + """

\b
Search engine API keys are read from environment variables:
  Google:    GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_ENGINE_ID, GOOGLE_SEARCH_API_ENDPOINT
  Brave:     BRAVE_SEARCH_API_KEY, BRAVE_SEARCH_API_ENDPOINT
  Tavily:    TAVILY_API_KEY
  Jina:      JINA_API_KEY
  Firecrawl: FIRECRAWL_API_KEY

\b
Examples:
  unique-websearch "quarterly earnings 2025"
  unique-websearch "AI regulation" -n 10
  unique-websearch "python tutorial" --no-crawl
  unique-websearch "climate policy" --engine brave -n 8
  unique-websearch "internal docs" --config ./project.json
"""
)


@click.command(help=HELP_TEXT)
@click.argument("query")
@click.option(
    "--fetch-size",
    "-n",
    default=None,
    type=int,
    help="Number of results to fetch (overrides config file value).",
)
@click.option(
    "--engine",
    "-e",
    default=None,
    help="Override search engine (e.g. google, brave, tavily).",
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
    engine: str | None,
    no_crawl: bool,
    config_path: str | None,
) -> None:
    try:
        search_engine_config, crawler_config = load_websearch_config(
            config_path=config_path,
            engine_override=engine,
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
