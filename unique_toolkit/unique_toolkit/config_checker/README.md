# Configuration Breaking Change Detector

A reusable, production-ready system for detecting configuration breaking changes in CI/CD pipelines before they hit production.

## Problem

Silent configuration breakages occur across commits when:
- A config schema changes (field removed, type changed)
- A config class is renamed or removed
- Default values shift in incompatible ways

These failures often don't surface until runtime in production, causing incidents.

**Solution**: This tool exports default configurations at merge-base and validates them at PR tip, catching breaking changes early with precise feedback.

## Quick Start (5 minutes)

### 1. Auto-Discovery (Most Configs)

By default, the system automatically discovers configs matching these patterns:
- Classes named `*Config` (e.g., `DatabaseConfig`, `ApiConfig`)
- Classes named `*Settings` (e.g., `Settings`, `DatabaseSettings`)
- Located in `config.py` files anywhere in your package
- Inheriting from Pydantic `BaseModel` or `BaseSettings`

**Example**: A package with this structure is auto-discovered:
```
mypackage/
├── config.py
│   └── class DatabaseSettings(BaseSettings): ...
├── core/
│   └── config.py
│       └── class CoreConfig(BaseModel): ...
```

No code changes needed! The CI will automatically check all configs.

### 2. Explicit Registration (Optional, for Edge Cases)

For non-standard scenarios, use the `@register_config()` decorator:

```python
from unique_toolkit.config_checker import register_config

@register_config(name="custom_database")
class DatabaseSettings(BaseSettings):
    host: str = "localhost"
    port: int = 5432
```

### 3. Opt-Out (for Internal Configs)

Mark configs to skip checking:

```python
class InternalDebugConfig(BaseModel):
    _skip_config_check = True
    internal_flag: bool = False
```

### 4. CI is Already Running

The workflow `.github/workflows/ci-config-check.yaml` automatically:
- Runs on every PR
- Exports defaults at merge-base
- Validates at PR tip
- Reports breaking changes in PR checks

No setup needed for most packages!

## How It Works

### High-Level Flow

```
1. Base Commit (Merge Base)
   ├─ Discover all configs
   └─ Export defaults to JSON

2. PR Tip Commit
   ├─ Discover configs with new schema
   └─ Validate old JSON against new schema
       ├─ Schema compatible? → PASS
       ├─ Schema incompatible? → FAIL with details
       └─ Defaults changed? → PASS but REPORT

3. CI Report
   ├─ Human-readable markdown report
   └─ Pass/fail decision for PR
```

### What Gets Checked

| Scenario | Result | Exit Code |
|----------|--------|-----------|
| Schema compatible | ✓ PASS | 0 |
| Field removed or type changed | ❌ FAIL | 1 |
| Config class removed/renamed | ❌ FAIL | 1 |
| Default values changed (schema OK) | ⚠️ PASS + REPORT | 0 |

## CLI Usage

The tool can be run manually locally for debugging:

### Export Defaults (run at base commit)

```bash
python -m unique_toolkit.config_checker export \
    --package ./tool_packages/unique_web_search \
    --output ./artifacts/
```

Output:
```
📦 Exporting configs from: ./tool_packages/unique_web_search
✓ Discovered 8 config(s)
✓ Export complete!
  - 8 exported
```

Generates:
- `artifacts/WebSearchSettings.json` - Default values
- `artifacts/manifest.json` - Export metadata

### Validate Against New Schema (run at tip commit)

```bash
python -m unique_toolkit.config_checker check \
    --artifacts ./artifacts/ \
    --package ./tool_packages/unique_web_search \
    --report-defaults
```

Output:
```
🔍 Validating configs from: ./tool_packages/unique_web_search
✓ Discovered 8 config(s) at tip
📊 Validation Results:
  - Total: 8
  - Valid: 7
  - Invalid: 1

❌ Validation FAILED
```

### Local Testing Workflow

Test breaking changes locally before committing:

```bash
# Save current state
git stash

# Export base defaults
git checkout main
python -m unique_toolkit.config_checker export \
    --package . \
    --output /tmp/base-defaults

# Restore your changes
git stash pop

# Validate
python -m unique_toolkit.config_checker check \
    --artifacts /tmp/base-defaults \
    --package .
```

## Understanding Reports

### Passing Check
```markdown
## ✓ All Configurations Compatible

### Summary
All 8 config(s) validated successfully.
```

### Failing Check with Details
```markdown
## ❌ Configuration Breaking Changes Detected

### 🔴 Schema Validation Failures

**unique_web_search.config.Settings**
- `google_search_api_key`: Removing a required field
- `max_results`: Type changed from `int` to `str`

**unique_stock_ticker.config.StockTickerConfig**
- `plotting_config.backend`: Unknown enum value 'matplotlib'

### 📊 Default Value Changes (non-breaking)

**unique_web_search.config.Settings**
- `web_search_mode`: "v1" → "v2"
- `active_search_engines`: ["google"] → ["google", "bing"]

### Summary
1 config(s) failed validation.
```

## Common Patterns

### Renaming a Config Class (Migration)

To rename without breaking CI:

**Before (base commit):**
```python
class WebSearchConfig(BaseModel):
    ...
```

**After (your PR):**
```python
# Keep old name temporarily with decorator
@register_config(name="WebSearchConfig")
class SearchConfig(BaseModel):
    ...
```

Once merged and stable, remove the decorator.

### Removing a Config (Intentional)

If a config is genuinely removed (not renamed), CI will fail. To proceed:

1. Understand the implications (what code uses this config?)
2. Update consuming code first
3. Remove the config in a separate PR with justification

### Changing Defaults Safely

Default changes that maintain schema compatibility pass CI but are reported:

```markdown
### 📊 Default Value Changes (non-breaking)
- `max_results`: 10 → 20
```

These are safe and don't break existing configs. The report is informational.

### Adding New Fields

New fields with defaults are safe:

```python
class ConfigV2(BaseModel):
    existing_field: str = "value"
    new_field: str = "new_default"  # Safe: has default
```

Fields added without defaults will cause validation errors for old configs missing them.

## Environment Variables & BaseSettings

The exporter **ignores environment variables** and exports only code-level defaults. This ensures:
- Reproducible exports across CI environments
- Detection of schema-level changes, not env-driven behavior
- Consistent baselines for comparison

**If env vars are detected during export:**
```
⚠️  1 warning(s):
  - Environment variable DB_HOST set during export (will be ignored, using code defaults)
```

This is normal in CI—the check continues with code defaults.

## Architecture

### Core Modules

- **registry.py**: Auto-discovers and manages config registration
- **exporter.py**: Exports config defaults to JSON
- **validator.py**: Validates old JSON against new schemas
- **differ.py**: Detects non-breaking default changes
- **cli.py**: Command-line interface
- **models.py**: Internal data structures

### Integration Points

**For Developers**:
- `@register_config()` decorator for explicit registration
- `_skip_config_check` attribute to exclude configs

**For CI/CD**:
- `.github/workflows/ci-config-check.yaml` runs on every PR
- `export` and `check` CLI commands for manual runs
- Markdown reports in GitHub Step Summary

## Troubleshooting

### Q: My config uses environment variables. Will this break CI?

**A:** No. The exporter uses code-level defaults only. You'll see a warning about env vars, but export continues with code defaults.

### Q: I renamed a config class. How do I avoid CI failure?

**A:** Use `@register_config(name="old_name")` on the new class during transition:

```python
@register_config(name="WebSearchSettings")
class SearchSettings(BaseSettings):  # Renamed from WebSearchSettings
    ...
```

Once stable, remove the decorator.

### Q: A field changed type but I coerced it in the schema. Will CI fail?

**A:** It depends. If Pydantic can coerce the old value to the new type, it passes. If not, CI fails. This is intentional—we want to catch type changes that might cause runtime errors.

### Q: Can I test this locally?

**A:** Yes! Use the CLI commands:

```bash
# At base
git checkout main
python -m unique_toolkit.config_checker export --package . --output /tmp/base

# At tip
git checkout your-branch
python -m unique_toolkit.config_checker check --artifacts /tmp/base --package .
```

### Q: The report says a config is "missing". What does that mean?

**A:** A config JSON file from base commit couldn't find a matching model at tip. Either:
- The config class was removed (breaking change)
- The config class was renamed without using `@register_config()`

To fix: Either restore the class or use `@register_config()` to map the old name.

### Q: Can I ignore a specific breaking change?

**A:** Not recommended (defeats the purpose), but you can:

1. **Temporarily opt-out** of checking:
   ```python
   class ConfigToRework(BaseModel):
       _skip_config_check = True
       ...
   ```

2. **Fix the schema** to maintain compatibility

3. **Create a migration guide** for users

The system is designed to catch issues early. If you need to skip, understand why.

## Performance

Typical CI impact per package: **30-60 seconds**

- Discovery: ~5s
- Export at base: ~15-20s
- Validation at tip: ~15-20s
- Report generation: ~5s

Impact is proportional to package complexity (number of configs, nesting depth).

## Limits & Assumptions

- **Pydantic v2 only**: Uses Pydantic v2 APIs (`model_validate`, `model_dump`)
- **Python 3.12+**: Requires Python 3.12 or later
- **Config files named `config.py`**: Auto-discovery looks for this filename
- **Classes in `config.py` only**: Explicit decorator required for configs in other files
- **SecretStr values**: Exported as plain strings in ephemeral CI artifacts (safe: artifacts auto-deleted)

## Future Enhancements

Potential improvements (not in MVP):

- [ ] Support other config frameworks (dataclasses, attrs)
- [ ] Warn-only mode for rollout phase
- [ ] Config change changelog generation
- [ ] Integration with migration scripts
- [ ] Custom validation hooks
- [ ] Cross-version testing (Python 3.11, 3.13)

## Development

The package source is in `unique_toolkit/unique_toolkit/config_checker/`:

```
config_checker/
├── __init__.py       # Public API
├── registry.py       # Config discovery
├── exporter.py       # Default export
├── validator.py      # Schema validation
├── differ.py         # Default comparison
├── cli.py            # CLI commands
├── models.py         # Data structures
└── tests/            # Test suite
```

### Running Tests

```bash
pytest unique_toolkit/unique_toolkit/config_checker/tests/ -v
```

### CLI Development

The CLI uses Click. To add a new command:

```python
@cli.command()
@click.option('--name', required=True)
def my_command(name):
    """My new command."""
    ...
```

## Support & Feedback

This tool is designed for early breaking change detection. If you encounter issues or have feature requests, please document them with:

1. Config structure (BaseModel vs BaseSettings)
2. The specific breaking change scenario
3. Expected vs actual behavior
4. Any custom validators or field configurations

## License

Proprietary - Unique AI
