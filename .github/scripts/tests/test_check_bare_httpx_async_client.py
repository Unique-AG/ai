from __future__ import annotations

import ast
import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "check_bare_httpx_async_client.py"
SPEC = importlib.util.spec_from_file_location("egress_check", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AsyncClientVisitorTest(unittest.TestCase):
    def _violations(self, source: str) -> list[tuple[int, int]]:
        visitor = MODULE.AsyncClientVisitor()
        visitor.visit(ast.parse(source))
        return visitor.violations

    def test_detects_module_and_imported_constructors(self) -> None:
        source = """
import httpx as hx
from httpx import AsyncClient as Client

first = hx.AsyncClient()
second = Client()
"""
        self.assertEqual(self._violations(source), [(5, 9), (6, 10)])

    def test_detects_partial_constructor(self) -> None:
        source = """
from functools import partial as factory
from httpx import AsyncClient

client_factory = factory(AsyncClient, timeout=10)
"""
        self.assertEqual(self._violations(source), [(5, 18)])

    def test_ignores_type_references_and_other_async_clients(self) -> None:
        source = """
import httpx
from google.genai.client import AsyncClient

annotation: httpx.AsyncClient
client = AsyncClient()
"""
        self.assertEqual(self._violations(source), [])


if __name__ == "__main__":
    unittest.main()
