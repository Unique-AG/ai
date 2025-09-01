# About this Documentation


## Technologies

### [MkDocs](https://www.mkdocs.org/)
MkDocs is used as a static site generator.

### [Entangles](https://entangled.github.io/#section-markdown)
Entangled is used to directly generate code from the snippets used in the documentation. This allows to verify that code in the documentation is always up to date. Additionally we a simple shell script `generate_examples.sh` to build fully type safe and linted examples.

## Workflow

1. `poetry run mkdocs serve -v` - Exposes the static site locally with hot reloading.
2. (a)(optional)  `poetry run entangled tangle` - Creates the initial `entangled` files under `./docs/.python_files` 
2. (b)`poetry run entangled watch` - Observed `entangled` files under `./docs/.python_files`. Any change in the markdown is synced to the python files and vice versa.
3. `generate_examples.sh` - Creates clean python files under `./docs/examples_from_docs` that can be included in the markdown files.