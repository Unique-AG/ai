"""Click entry point for the unique-websearch CLI."""

from __future__ import annotations

import sys

import click

from unique_web_search.cli import __version__
from unique_web_search.cli.cli_config import (
    CLIConfigError,
    load_crawler_config,
    load_search_engine_config,
)
from unique_web_search.cli.commands.crawl import cmd_crawl
from unique_web_search.cli.commands.search import cmd_search

MAIN_HELP = """\
Two-phase web search from the terminal.

Phase 1 — search: query a search engine, get back URLs and snippets.
Phase 2 — crawl:  fetch full page content for selected URLs.

Engine and crawler are determined by environment variables
(ACTIVE_SEARCH_ENGINES / ACTIVE_INHOUSE_CRAWLERS), matching
the server-side configuration.

\b
Environment variables (engine / crawler selection):
  ACTIVE_SEARCH_ENGINES       Which engine to use (e.g. google)
  ACTIVE_INHOUSE_CRAWLERS     Which crawlers are available (e.g. basic, crawl4ai)

\b
Environment variables (API keys — set for your configured engine):
  Google:    GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_ENGINE_ID, GOOGLE_SEARCH_API_ENDPOINT
  Brave:     BRAVE_SEARCH_API_KEY, BRAVE_SEARCH_API_ENDPOINT
  Tavily:    TAVILY_API_KEY
  Jina:      JINA_API_KEY
  Firecrawl: FIRECRAWL_API_KEY
"""


@click.group(help=MAIN_HELP)
@click.version_option(version=__version__, prog_name="unique-websearch")
@click.option(
    "--config",
    "-c",
    "config_path",
    default=None,
    type=click.Path(),
    help="Path to JSON config file (default: ~/.unique-websearch.json).",
)
@click.pass_context
def main(ctx: click.Context, config_path: str | None) -> None:
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path


SEARCH_HELP = """\
Search the web and return URLs with snippets.

\b
Examples:
  unique-websearch search "quarterly earnings 2025"
  unique-websearch search "AI regulation" -n 10
  unique-websearch search "python tutorial" --json
"""


@main.command("search", help=SEARCH_HELP)
@click.argument("query")
@click.option(
    "--fetch-size",
    "-n",
    default=None,
    type=int,
    help="Number of results to fetch (default: 50, or from config).",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON (for piping to other tools).",
)
@click.pass_context
def search_cmd(
    ctx: click.Context,
    query: str,
    fetch_size: int | None,
    output_json: bool,
) -> None:
    config_path: str | None = ctx.obj["config_path"]
    try:
        engine_config = load_search_engine_config(config_path=config_path)
    except CLIConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    try:
        result = cmd_search(
            search_engine_config=engine_config,
            query=query,
            fetch_size=fetch_size,
            output_json=output_json,
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(result)


CRAWL_HELP = """\
Crawl a list of URLs and return their full page content.

URLs can be provided as arguments or piped via stdin (one per line).

\b
Examples:
  unique-websearch crawl https://example.com https://other.com
  unique-websearch crawl --parallel 5 https://a.com https://b.com
  echo "https://example.com" | unique-websearch crawl --stdin
  unique-websearch search "query" --json | jq -r '.[].url' | unique-websearch crawl --stdin
"""


@main.command("crawl", help=CRAWL_HELP)
@click.argument("urls", nargs=-1)
@click.option(
    "--parallel",
    "-p",
    default=10,
    type=int,
    show_default=True,
    help="Number of URLs to crawl in parallel.",
)
@click.option(
    "--stdin",
    "from_stdin",
    is_flag=True,
    help="Read URLs from stdin (one per line).",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON.",
)
@click.pass_context
def crawl_cmd(
    ctx: click.Context,
    urls: tuple[str, ...],
    parallel: int,
    from_stdin: bool,
    output_json: bool,
) -> None:
    config_path: str | None = ctx.obj["config_path"]

    url_list = list(urls)
    if from_stdin:
        stdin_urls = [
            line.strip() for line in click.get_text_stream("stdin") if line.strip()
        ]
        url_list.extend(stdin_urls)

    if not url_list:
        click.echo(
            "Error: no URLs provided. Pass URLs as arguments or use --stdin.", err=True
        )
        sys.exit(1)

    try:
        crawler_config = load_crawler_config(config_path=config_path)
    except CLIConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    try:
        result = cmd_crawl(
            crawler_config=crawler_config,
            urls=url_list,
            parallel=parallel,
            output_json=output_json,
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(result)
