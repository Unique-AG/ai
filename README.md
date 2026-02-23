# ai
Unique AI libraries, tools and resources for public consumption.


# Developer instructions

## Python, Poetry & uv setup

Most packages in this monorepo require **Python 3.12**. `unique_sdk` additionally supports Python 3.11+.
Poetry packages use **Poetry 2.1.3**; `unique_mcp` and `unique_web_search` use **uv**.

### Option A — mise (recommended for local development)

[mise](https://mise.jdx.dev) manages Poetry, uv, and Python versions automatically. After cloning:

```shell
# Install mise
curl https://mise.run | sh

# Install Poetry 2.1.3 + uv (pinned in .mise.toml)
mise install

# Set your Python version (written to .mise.local.toml, which is gitignored)
mise use python@3.12        # most packages
# cd unique_sdk && mise use python@3.11   # sdk only
```

CI also uses `jdx/mise-action` which reads `.mise.toml` for Poetry/uv versions automatically.

### Option B — manual setup

```shell
# Python (pyenv, asdf, or system package manager)
python --version   # should be 3.12.x

# Poetry
pipx install poetry==2.1.3

# uv (for unique_mcp / unique_web_search)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installing a package

Poetry packages:
```shell
cd <package_dir>
poetry install
```

uv packages (`unique_mcp`, `unique_web_search`):
```shell
cd <package_dir>
uv sync --locked
```

## Pre-commit hooks

The python code in this repository is strictly checked for linting, formatting and imports sorting.
Please use git `pre-commit` hooks to ensure your commits always remain compatible and clean.

Run the below commands to setup your pre-commit hooks as needed.

```shell
pip install pre-commit
pre-commit install
```

## License

Refer to [`LICENSE.md`](./LICENSE.md).

## Security

Refer to [`SECURITY.md`](./SECURITY.md).