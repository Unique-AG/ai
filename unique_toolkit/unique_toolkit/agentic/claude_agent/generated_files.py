"""
Generated files handling for Claude Agent SDK integration.

This module will contain helpers for post-processing Claude's output and
constructing structured artifacts that the downstream pipeline expects.
Naming aligns with DisplayCodeInterpreterFilesPostProcessor conventions.

Responsibilities:
- parse_references(): extracts [source0], [source1], ... markers from the
  accumulated text and constructs Reference objects for ReferenceManager.
- build_debug_info(): collects tool call events, turn counts, budget usage,
  and skills invoked from the SDK stream into a debug_info dict for the
  final message.
- Generated file tracking: when code execution is enabled (Bash/Write tools),
  this module tracks files written during the session so they can be surfaced
  to the user via DisplayCodeInterpreterFilesPostProcessor.

These helpers are called after Claude's autonomous loop exits, before
EvaluationManager, PostprocessorManager, and ReferenceManager run.
"""

from __future__ import annotations
