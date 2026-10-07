# Import rules

`poe check-imports` enforces this. The machine source is `[tool.importlinter]` in `pyproject.toml`.

| Importer | May import | Must not import |
| --- | --- | --- |
| `contract` | nothing else in this package | `app` |
| `app` | `contract` and the layers it wires | a layer that is not listed here |

The skeleton forbids `contract` from importing `app`. When you add a layer, add a row here and add that layer to the forbidden list for `contract` in `pyproject.toml`. An edge that is not in the table is forbidden.
