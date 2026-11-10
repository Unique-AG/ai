# About this Documentation


## Technologies

### [MkDocs](https://www.mkdocs.org/)
MkDocs is used as a static site generator.

### [Entangles](https://entangled.github.io/#section-markdown)
Entangled is used to directly generate code from the snippets used in the documentation. This allows to verify that code in the documentation is always up to date. Additionally we a simple shell script `generate_examples.sh` to build fully type safe and linted examples.

## Workflow

1. `uv run mkdocs serve -v` - Exposes the static site locally with hot reloading.
2. (a)(optional)  `uv run entangled tangle` - Creates the initial `entangled` files under `./docs/.python_files` 
2. (b)`uv run entangled watch` - Observes `entangled` files under `./docs/.python_files`. Any change in the markdown is synced to the python files and vice versa.
3. `generate_examples.sh` - Creates clean python files under `./docs/examples_from_docs` that can be included in the markdown files. It also adds a VS Code cell marker (`# %%`) after the `# /// script` block (or at the top when there is no script metadata) so examples stay interactive in the IDE without breaking `uv run`.

## Running examples (readers)

Runnable scripts under `docs/examples_from_docs/` start with [uv inline script metadata](https://docs.astral.sh/uv/guides/scripts/#declaring-script-dependencies) (`# /// script`). You can execute them without a local project checkout:

```bash
uv run path/to/example.py
```

`uv` needs network access on first run to download `unique-toolkit`, `unique-sdk`, and their dependencies. Set the required `UNIQUE_*` environment variables (see [Getting started](setup/getting_started.md)) before running examples that call the platform API.

### "Run this example" download policy

`Run this example` blocks in the docs must fetch the script at an **immutable release tag**, never from a branch tip. The pattern is:

1. Resolve `RELEASE` to the latest non-prerelease `unique-toolkit-v*` tag via the GitHub Releases API (with optional `RELEASE=unique-toolkit-v<version>` override and optional `GH_TOKEN` for higher rate limits).
2. `curl` the example from `https://raw.githubusercontent.com/Unique-AG/ai/${RELEASE}/...`.
3. `uv run` it.

Do not hand-write snippets that `curl … /<branch-name>/… | uv run` from a branch tip — branch tips are mutable and a forced push can swap the script bytes a reader is about to execute. See `docs/modules/examples/content/content-folder.md` for the canonical block to copy.

When adding or updating tangled examples, include `<<example-script-deps>>` as the first line of every Entangled composition that targets `docs/.python_files/`. The block is defined in `docs/setup/_script_dependencies.md`.

Do not add `<<example-script-deps>>` when the composition already includes a block that carries it (for example `<<full_sse_setup_with_services>>`, which starts with script metadata). Duplicate `# /// script` headers break `uv run`.

Keep `# /// script` at the top of the generated file: list `<<full_sse_setup_with_services>>` (or `<<example-script-deps>>`) before any other imports, and place extra imports (for example `import time`) inside the event loop body, not above the setup block.

Use `<<example-script-deps-langchain>>` from `docs/setup/_script_dependencies_langchain.md` for LangChain examples (requires the `langchain` extra).

## Running examples (local development)

Against **branch source** (before PyPI publish), override inline PyPI pins with path deps:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
uv run --no-project \
  --with "unique-sdk @ file://${REPO_ROOT}/unique_sdk" \
  --with "unique-toolkit @ file://${REPO_ROOT}/unique_toolkit" \
  unique_toolkit/docs/examples_from_docs/standalone_setup.py
```

Helper scripts (from repo root; `unique.env` in repo root or `ENVIRONMENT_FILE_PATH` set):

- **Smoke** (syntax + imports, no API): `uv sync --locked --package unique_sdk --package unique_toolkit && uv sync --package unique_toolkit --extra langchain && uv run python unique_toolkit/scripts/validate_doc_examples.py`
- **Run all** (live tenant required): `unique_toolkit/scripts/run_all_doc_examples.sh`
