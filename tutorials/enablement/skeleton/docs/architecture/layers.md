# Layers

Imports go toward `contract`. `contract` imports nothing else in this package.

| Layer | Owns | Must not own |
| --- | --- | --- |
| `contract` | Frozen models and other values | I/O, framework clients, the composition root |
| composition root (`app.py`) | Wiring for an MCP or an API | Business rules |

A tool or a library has no composition root. Delete `app.py`.

Add a layer by adding a row to this table and a contract in `pyproject.toml` in the same change. These names are roles, not required folders:

- A **service class** is the keyword-only object callers use. Read `tutorials/enablement/references/service.md` in the ai repo when you add one.
- An **adapter** talks to something outside the package. Read `tutorials/enablement/references/adapter.md` when you add one.
- A **facade** forwards to other service classes and adds no logic. Read `tutorials/enablement/references/facade.md` when you add one.
- A **component** is one behaviour in its own module.
- A **policy** is a pure decision a loop calls.
- An **integration** talks to one external system and does not import a sibling integration.

Read a reference when you add that role. Do not copy `unique_toolkit/experimental/` folder names unless this package already uses them.
