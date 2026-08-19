"""Run-scoped collection of language-model invocation usage."""

from unique_toolkit.language_model.invocation_stats import InvocationStatsCollector

collector = InvocationStatsCollector("internal_search")
