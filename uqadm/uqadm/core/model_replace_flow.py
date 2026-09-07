"""Orchestration shared by the space and folder ``model-replace`` commands.

The two commands differ in what they load, how they write and what they call a
document, but the ``--file`` flow around that — parse, rewrite, report the
matched paths, honour ``--dry-run``, emit — is identical, so it lives here.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

import typer
import yaml

from uqadm.core.json_types import JsonObject
from uqadm.core.model_refs import ModelRef, replace_model_refs
from uqadm.core.payload_files import load_json_or_yaml_mapping

#: Emits a document to a path, or to stdout when the path is ``None``.
DocumentWriter = Callable[[JsonObject, Path | None], None]


def echo_refs(refs: list[ModelRef], *, err: bool = False) -> None:
    """Print one matched path per line, indented under a preceding summary."""
    for ref in refs:
        typer.echo(f"  {ref.path}", err=err)


def run_file_replacement(
    file_path: Path,
    *,
    from_model: str,
    to_value: str | JsonObject,
    output: Path | None,
    dry_run: bool,
    label: str,
    write: DocumentWriter,
) -> None:
    """Rewrite ``from_model`` in a local document and emit the result.

    ``label`` names the document in messages ("ingestion config", "snapshot")
    and ``write`` renders it, so callers keep their own format handling.
    """
    try:
        document = load_json_or_yaml_mapping(file_path)
    except json.JSONDecodeError as exc:
        typer.echo(f"Invalid JSON in {label} file: {exc}", err=True)
        sys.exit(2)
    except yaml.YAMLError as exc:
        typer.echo(f"Invalid YAML in {label} file: {exc}", err=True)
        sys.exit(2)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        sys.exit(2)

    new_document, refs = replace_model_refs(document, from_model, to_value)
    if not refs:
        typer.echo(f"No occurrences of {from_model!r} found in {file_path}.", err=True)
    else:
        typer.echo(
            f"{len(refs)} replacement(s) of {from_model!r} in {file_path}:", err=True
        )
        echo_refs(refs, err=True)

    if dry_run:
        typer.echo("Dry-run: no output written.", err=True)
        return
    write(new_document, output)
    if output is not None:
        typer.echo(f"Wrote rewritten {label} to {output}.", err=True)
