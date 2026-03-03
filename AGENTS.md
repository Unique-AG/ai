# Agent Guidelines

This file tells AI coding agents (Claude Code, Cursor, Copilot, etc.) how to work in this repo.

These guidelines apply to `unique_toolkit/` and `tool_packages/`. The `unique_sdk/` has separate constraints — do not modify it without explicit instruction.

---

## Repo Overview

```
unique_toolkit/   # Core Python library (main package)
tool_packages/    # Individual tools (web_search, deep_research, …)
connectors/       # Data source connectors
postprocessors/   # Post-processing modules
unique_sdk/       # SDK (do not modify without explicit instruction)
unique_orchestrator/
unique_mcp/
```

Each sub-project has its own `pyproject.toml`, `CHANGELOG.md`, and virtual environment.

---

## Workflow Rules

**Before every commit** (inside the relevant sub-project directory):

```bash
poe lint       # ruff check — fix lint errors
poe format     # ruff format — auto-format code
poe typecheck  # basedpyright — no type errors allowed
poe test       # pytest — all tests must pass
```

- Pre-commit hooks run `ruff` and `ruff-format` automatically on staged files.
- Never use `--no-verify` to bypass hooks.
- Never suppress type errors with `# type: ignore` without a comment explaining why.
- Never use `# noqa` without a comment. Disable rules repo-wide in `pyproject.toml` instead.
- Target Python is **3.12**. Use native syntax: `X | Y` not `Union[X, Y]`, `list[str]` not `List[str]`.

---

## Release & PR Conventions

### Commit messages

Use the `git-conventional-commits` skill for the full format and workflow.

**Branch naming** — always start from a Jira ticket and embed the ticket ID in the branch name:
```
<type>/[<scope>/]<un-XXXXX>-<short-slug>
```
Examples: `feat/toolkit/un-17684-pandoc-converter`, `fix/un-17492-pyproject-pr-changes`

The ticket ID in the branch name lets tooling (and reviewers) trace every branch back to its ticket without reading commit messages.

**Commit format:**
```
type(scope): description

Refs: UN-XXXXX
```

- **Jira ticket** goes in the commit body as `Refs: UN-XXXXX` — include it whenever the work is tracked in Jira. If the branch already contains the ticket ID it can often be inferred automatically.
- **`(#PR-number)`** suffix you see in the git log is appended automatically by GitHub on merge — do not write it manually.
- Scope names: `toolkit`, `web-search`, `deep-research`, `sdk`, `orchestrator`, `mcp`, `ci`, `docs`.

Examples:
```
feat(toolkit): add pandoc markdown converter

Refs: UN-17684
```
```
chore: update dev dependencies
```

### Changelog & version bump

Use the `changelog-pyproject` skill — it already knows the correct file paths (`unique_toolkit/CHANGELOG.md`, etc.) and the semver rules for this project.

### PRs

- One concern per PR. If a change touches unrelated areas, split it.
- PR title follows the same `type(scope): description` convention as commits.

---

## Coding Conventions

### Error handling

- Raise `CommonException(user_message=..., error_message=..., exception=original)` — keep user-facing and technical messages separate.
- Use `InfoExceptionForAi` when the LLM needs to communicate the error to the user.
- Use `ConfigurationException` for missing/invalid config (should surface at startup, not at request time).
- Define domain-specific exception types (e.g. `LockedAgenticTableError`) rather than reusing `CommonException` for every case.
- Never swallow exceptions silently. Always log or re-raise.
- Use exception chaining: `raise MyException(...) from original_exc`.
- Keep `try` blocks small — only wrap the lines that can actually raise.
- At API/entry-point boundaries log with `exc_info=True` and return the appropriate HTTP status; do not let raw exceptions leak to callers.

```python
from unique_toolkit._common.exception import CommonException

try:
    result = await external_call()
except Exception as exc:
    raise CommonException(
        user_message="The operation failed. Please try again.",
        error_message=f"external_call failed: {exc}",
        exception=exc,
    ) from exc
```

### Logging

- Always name the module-level logger `_LOGGER` (private module constant). Use `get_logger(__name__)` from `unique_toolkit.app` — it centralises future changes (name prefix, structured logging) without touching every call site.
- In `unique_toolkit` domain modules use `get_logger(f"toolkit.{DOMAIN_NAME}.{__name__}")` if you need a domain-scoped prefix; otherwise `get_logger(__name__)` is fine.
- Accept an optional `logger: logging.Logger | None = None` in service `__init__`, defaulting to `get_logger(__name__)`. This keeps production call sites simple and lets tests inject a logger.
- Use `%s` formatting in log calls (not f-strings): `_LOGGER.warning("Status %s, retrying", status)`.
- At API/entry-point boundaries (webhook handlers, FastAPI routes), log exceptions with `exc_info=True` so the full traceback is captured: `_LOGGER.error("Error parsing event: %s", e, exc_info=True)`.

```python
from unique_toolkit.app import get_logger
_LOGGER = get_logger(__name__)

class MyService:
    def __init__(self, ..., logger: logging.Logger | None = None):
        self._logger = logger or get_logger(__name__)
```

### Settings (environment variables)

Settings are loaded once at startup from env vars and must be immutable.

- Use `pydantic-settings` `BaseSettings`. Never use plain dicts or raw `os.environ` reads.
- Always set `frozen=True` in `SettingsConfigDict` — settings must not change after load.
- Wrap secrets in `SecretStr`. Never store credentials as `str`.
- Use `AliasChoices` so both short (`API_KEY`) and namespaced (`UNIQUE_APP_KEY`) env var names work.
- Decorate every settings class with `@register_config()` for global discovery.
- Add `model_validator(mode="after")` calling `warn_about_defaults()` to warn when defaults are still in use.

```python
@register_config()
class MySettings(BaseSettings):
    api_key: SecretStr = Field(
        default=SecretStr("dummy"),
        validation_alias=AliasChoices("my_api_key", "API_KEY"),
    )
    model_config = SettingsConfigDict(env_prefix="my_", extra="ignore", frozen=True)

    @model_validator(mode="after")
    def _warn(self) -> Self:
        return warn_about_defaults(self)
```

### Configuration (request-time)

Configuration that arrives per-request (via event payload, API body, or tool call) is separate from env-based settings.

- Use plain `pydantic BaseModel` — not `BaseSettings`.
- Validate at the boundary (service constructor or route handler); never pass raw dicts further into the call stack.
- Keep request-time config immutable within a single request where possible (`model_config = ConfigDict(frozen=True)`).

```python
from pydantic import BaseModel, ConfigDict

class MyToolConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_results: int = 10
    language: str = "en"
```

### Type annotations

- All code must be fully annotated. `basedpyright` standard mode is enforced.
- Use `Pydantic BaseModel` for structured data crossing any boundary (API, config, service return).
- Use `Protocol` for structural duck-typing contracts; use `ABC` when you own the class hierarchy.
- Use `Generic[T]` + `TypeVar` (or Python 3.12 `class Foo[T]:`) for reusable parameterised components.
- Import heavy types under `TYPE_CHECKING` to avoid circular imports.

### Tool registration

Register tools with `ToolFactory` at **module load time** (end of the tool's `service.py`):

```python
# bottom of unique_toolkit/agentic/tools/a2a/tool/service.py
ToolFactory.register_tool(SubAgentTool, SubAgentToolConfig)
```

### Testing

Use the `python-testing` skill for naming conventions, docstring format, AAA structure, fixture patterns, and mocking rules.

Repo-specific additions:
- `asyncio_mode = "auto"` is already configured — async tests work without `@pytest.mark.asyncio`.
- Use class-based test suites with `@pytest.fixture(autouse=True)` for shared setup rather than module-level fixtures.
- Build test objects via factory functions (e.g. `get_event_obj(...)`) in `test_obj_factory.py` or `conftest.py` rather than inlining construction.
- Markers in use: `@pytest.mark.ai`, `@pytest.mark.verified`, `@pytest.mark.wip` — all must be declared (enforced by `--strict-markers`).
- For tests that modify **global state** (e.g. `ToolFactory` class-level registries), save and restore state in `setup_method` / `teardown_method`:

```python
class TestToolFactory:
    def setup_method(self):
        self.original_tool_map = ToolFactory.tool_map.copy()
        ToolFactory.tool_map.clear()

    def teardown_method(self):
        ToolFactory.tool_map.clear()
        ToolFactory.tool_map.update(self.original_tool_map)
```

```python
class TestMyService:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = MyService(company_id="co", user_id="u")

    @pytest.mark.ai
    def test_process__when_input_is_empty__raises_value_error(self) -> None:
        """
        Purpose: Verify empty input is rejected early.
        Why this matters: Prevents downstream failures from propagating.
        Setup summary: Call process() with empty string, expect ValueError.
        """
        # Arrange / Act / Assert
        with pytest.raises(ValueError):
            self.service.process("")
```

### Patterns to avoid

- Don't use `dict` for structured data — define a Pydantic model.
- Don't catch bare `except Exception` at the top level — be specific or re-raise with context.
- Don't use `Union[X, Y]`, `Optional[X]`, `List[X]` — use `X | Y`, `X | None`, `list[X]` (Python 3.10+).
- Don't import from `_common` outside of `unique_toolkit` — it's internal. Code in `tool_packages/` must depend on the public toolkit API (e.g. `unique_toolkit.app.get_logger`, exported services).
- Don't create loggers inside methods — use module-level `_LOGGER = get_logger(__name__)`.
- Don't add `# type: ignore` or `# noqa` without explaining why in a comment.

---

## Code Review Checklist

Use this when reviewing or self-reviewing any Python PR.

### Style
- Ruff passes (`poe lint`, `poe format`).
- Imports: stdlib → third-party → local; no wildcard imports.
- Naming: `snake_case` for functions/variables, `CamelCase` for classes.
- Docstrings explain the *why*, not the *what*. Public APIs have docstrings.

### Structure
- Each function/method does one thing (single responsibility).
- No unnecessary complexity — simplest solution that solves the problem.
- Reusable logic extracted into functions or classes; no copy-paste.

### Error handling
- Specific exception types — no bare `except:` or `except Exception:` without re-raise.
- Custom domain exceptions where they add clarity.
- API boundaries log with `exc_info=True` and return appropriate status.

### Testing
- New behaviour has at least two unit tests (happy path + failure/edge case).
- External dependencies are mocked — tests are deterministic and fast.
- Global state (e.g. ToolFactory) is saved and restored in `setup_method`/`teardown_method`.
- Tests follow naming and docstring conventions (see `python-testing` skill).

### Security
- No secrets, passwords, or API keys in code — use env/settings.
- External inputs validated via Pydantic or explicit checks at boundaries.

### PR checklist
- [ ] `poe lint`, `poe typecheck`, `poe test` all pass locally
- [ ] Settings: `BaseSettings` + `frozen=True` + `@register_config()`; no secrets as plain `str`
- [ ] Config: request-time config uses `BaseModel`; validated at boundary
- [ ] Logging: `_LOGGER = get_logger(__name__)` at module level; optional injectable logger in new services
- [ ] Tests: naming and docstrings per `python-testing` skill; shared state restored if mutated
- [ ] Types: type hints on new/changed public APIs; basedpyright clean
- [ ] Changelog and version bumped if user-facing change (use `changelog-pyproject` skill)
