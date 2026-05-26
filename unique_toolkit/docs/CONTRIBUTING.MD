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
3. `generate_examples.sh` - Creates clean python files under `./docs/examples_from_docs` that can be included in the markdown files.

## Running examples (readers)

Runnable scripts under `docs/examples_from_docs/` start with [uv inline script metadata](https://docs.astral.sh/uv/guides/scripts/#declaring-script-dependencies) (`# /// script`). You can execute them without a local project checkout:

```bash
uv run path/to/example.py
```

`uv` needs network access on first run to download `unique-toolkit`, `unique-sdk`, and their dependencies. Set the required `UNIQUE_*` environment variables (see [Getting started](setup/getting_started.md)) before running examples that call the platform API.

When adding or updating tangled examples, include `<<example-script-deps>>` as the first line of every Entangled composition that targets `docs/.python_files/`. The block is defined in `docs/setup/_script_dependencies.md`.

Do not add `<<example-script-deps>>` when the composition already includes a block that carries it (for example `<<full_sse_setup_with_services>>`, which starts with script metadata). Duplicate `# /// script` headers break `uv run`.
