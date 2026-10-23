from unique_toolkit.monitoring import MetricNamespace

m = MetricNamespace("unique_web_search")

# Search Engine (P1)
search_duration = m.histogram(
    "search_duration_seconds", "Search API latency", ["engine"]
)
search_total = m.counter("search_total", "Search calls by engine", ["engine"])
search_errors = m.counter(
    "search_errors_total", "Search failures", ["engine", "error_type"]
)
custom_api_url_safety_report = m.counter(
    "custom_api_url_safety_report_total",
    "Report-only URL safety outcomes for legacy Custom API searches",
    ["outcome", "reason_category"],
)
grounding_parse_failures = m.counter(
    "grounding_parse_failures_total",
    "Grounded agent answers that yielded no usable sources",
    ["engine", "reason"],
)
grounding_dropped_citations = m.counter(
    "grounding_dropped_citations_total",
    "Citations dropped from grounded agent answers because they failed validation",
    ["engine", "reason"],
)
grounding_dropped_lines = m.counter(
    "grounding_dropped_lines_total",
    "Answer lines dropped from grounded agent answers",
    ["engine", "reason"],
)

# End-to-End Tool (P1)
tool_duration = m.histogram(
    "tool_duration_seconds",
    "WebSearchTool.run() duration",
    ["executor_version"],
)
tool_errors = m.counter(
    "tool_errors_total",
    "Tool-level exceptions (infra failures, timeouts, crashes)",
    ["executor_version", "error_type"],
)
tool_empty_results = m.counter(
    "tool_empty_results_total",
    "Tool runs that completed without returning any content chunks",
    ["executor_version"],
)

# LLM / Processing (P2)
llm_duration = m.histogram("llm_duration_seconds", "LLM call duration", ["purpose"])
llm_errors = m.counter(
    "llm_errors_total", "LLM call failures", ["purpose", "error_type"]
)

# Crawl / Scrape (P3)
crawl_duration = m.histogram("crawl_duration_seconds", "Crawl latency", ["crawler"])
crawl_errors = m.counter(
    "crawl_errors_total", "Crawl failures", ["crawler", "error_type"]
)
crawl_blocked = m.counter(
    "crawl_blocked_total",
    "Crawl targets blocked by URL safety policy",
    ["reason_category"],
)
