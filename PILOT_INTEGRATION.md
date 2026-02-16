"""Pilot integration guide and test scenarios.

This document describes how to pilot the config_checker in a real package
and validate that it catches actual breaking changes.
"""

# Pilot Integration Steps

## 1. Target Package: unique_web_search

The `unique_web_search` package is ideal for pilot because:
- Has multiple config classes (Settings, GoogleSearchSettings, etc.)
- Uses BaseSettings with environment variables
- Good complexity for testing real scenarios

## 2. Enable CI Check

The workflow `.github/workflows/ci-config-check.yaml` already includes `web_search`.
On next PR to `unique_toolkit`:
- Config check will run automatically
- Will report any breaking changes

## 3. Test Scenarios (Create PRs with these changes)

### Scenario 1: Field Removal (Should FAIL)
**File**: `tool_packages/unique_web_search/src/unique_web_search/config.py`

```python
# BEFORE (base)
class Settings(BaseSettings):
    google_search_api_key: str | None = None
    web_search_mode: str = "v2"

# AFTER (your PR) - REMOVE a field
class Settings(BaseSettings):
    web_search_mode: str = "v2"
    # google_search_api_key removed → BREAKS
```

**Expected CI Result**: ❌ FAIL
- Error: `google_search_api_key field missing from validation`

### Scenario 2: Type Change (Should FAIL)
```python
# BEFORE
class Settings(BaseSettings):
    max_results: int = 10

# AFTER - Change type
class Settings(BaseSettings):
    max_results: str = "10"  # Changed to string → BREAKS
```

**Expected CI Result**: ❌ FAIL
- Error: `Input should be a valid integer` (old value was int)

### Scenario 3: Default Change (Should PASS + REPORT)
```python
# BEFORE
class Settings(BaseSettings):
    web_search_mode: str = "v1"
    timeout: int = 30

# AFTER - Change defaults only
class Settings(BaseSettings):
    web_search_mode: str = "v2"  # Changed default
    timeout: int = 60  # Changed default
```

**Expected CI Result**: ✓ PASS
- Report: Default changes detected (non-breaking)

### Scenario 4: Add Required Field (Should FAIL)
```python
# BEFORE
class Settings(BaseSettings):
    api_key: str = "default"

# AFTER - Add required field
class Settings(BaseSettings):
    api_key: str = "default"
    new_required_field: str  # No default → BREAKS
```

**Expected CI Result**: ❌ FAIL
- Error: `Field required`

### Scenario 5: Add Optional Field (Should PASS)
```python
# BEFORE
class Settings(BaseSettings):
    api_key: str = "default"

# AFTER - Add optional field with default
class Settings(BaseSettings):
    api_key: str = "default"
    new_optional_field: str = "default"  # Has default → OK
```

**Expected CI Result**: ✓ PASS

### Scenario 6: Rename with @register_config (Should PASS)
```python
# BEFORE
class WebSearchSettings(BaseSettings):
    host: str = "api.example.com"
    timeout: int = 30

# AFTER - Rename but use decorator to map old name
@register_config(name="WebSearchSettings")  # CRITICAL: Use exact old name
class SearchSettings(BaseSettings):  # New name
    host: str = "api.example.com"  # Must be compatible!
    timeout: int = 30
    # ... any new optional fields with defaults are OK
```

**Expected CI Result**: ✓ PASS

**How it works:**
1. At base: `WebSearchSettings.json` is exported
2. At tip: 
   - Auto-discovery finds `SearchSettings` class
   - Decorator explicitly registers it as `"WebSearchSettings"`
   - Registry now has both: `"SearchSettings"` → SearchSettings and `"WebSearchSettings"` → SearchSettings
3. During validation:
   - Validator loads `WebSearchSettings.json`
   - Looks up `"WebSearchSettings"` in registry → finds SearchSettings class
   - Validates old JSON against new schema → ✓ PASS (if schema compatible)

**Critical Requirements:**
- ✓ Decorator name MUST match old class name exactly
- ✓ New schema must be backward-compatible (all old fields still exist with same types)
- ✓ New optional fields are OK (they have defaults)
- ✓ This is a **temporary pattern** for migration - remove decorator once stable

**What happens WITHOUT the decorator?**
- If you forget `@register_config()`, validator looks for "SearchSettings" in artifacts
- It won't find `WebSearchSettings.json` → CI ❌ FAILS
- This is good! It forces you to be explicit about renames

## 4. Pilot Checklist

- [ ] Deploy `config_checker` code to `unique_toolkit`
- [ ] Enable `.github/workflows/ci-config-check.yaml` (already included)
- [ ] Create test PR with Scenario 1 (field removal)
  - [ ] Verify CI fails with clear error message
  - [ ] Review report in PR checks
- [ ] Create test PR with Scenario 3 (default change)
  - [ ] Verify CI passes
  - [ ] Verify report shows changes detected
- [ ] Create test PR with Scenario 6 (rename)
  - [ ] Verify @register_config works
  - [ ] Verify CI passes despite rename
- [ ] Have 1-2 developers review reports
  - [ ] Are error messages clear?
  - [ ] Is the remediation obvious?
- [ ] Monitor for false positives over 2 weeks
- [ ] Collect feedback on UX and helpfulness

## 5. Success Metrics

**MVP Pilot Success**:
- ✓ Catches test breaking changes
- ✓ No false positives
- ✓ Reports are understandable
- ✓ CI time impact < 2 minutes
- ✓ Developers find it "helpful" or "very helpful"

**Rollout Ready**:
- ✓ Documentation reviewed by team
- ✓ Integrated in 3+ packages
- ✓ Zero config-related production incidents during 4-week period

## 6. Common Pilot Findings

Based on similar tools:

**Finding 1: BaseSettings env vars**
- Some configs might load from env vars in dev
- The "warning" during export is helpful context
- No action needed—export continues with code defaults

**Finding 2: Custom validators**
- Some configs use `@field_validator` or `@model_validator`
- Pydantic's `model_validate` respects validators
- Validators might reject old values → CI fails
- This is correct behavior (catching incompatible changes)

**Finding 3: Discriminated unions**
- Configs with discriminator fields are well-supported
- Changes to discriminator values are caught
- Test with `unique_deep_research` if possible

**Finding 4: Optional fields vs None defaults**
- Pydantic v2 distinguishes `str | None` with default None
- Changes in optionality are caught correctly

## 7. Next Steps After Pilot

1. **If successful**: Roll out to other packages
   - Priority: High-change packages (unique_swot, unique_web_search)
   - Batch: Post-pilot review, add 3-5 more packages
   
2. **If issues found**: Document and patch
   - Common patterns emerge
   - Edge cases refined
   - Tests expanded

3. **Monitor & iterate**:
   - Track CI time over weeks
   - Collect real breaking change statistics
   - Measure false positive rate
   - Adjust warnings/errors based on feedback

## 8. Rollout Plan (Post-Pilot)

**Week 1-2 (Pilot)**:
- unique_web_search only
- Collect feedback
- Fix issues

**Week 3-4 (Expand)**:
- Add: unique_swot, unique_deep_research, unique_stock_ticker
- Train teams on interpreting reports
- Document common scenarios

**Week 5-8 (Full Rollout)**:
- Add: Remaining packages
- Team sync on best practices
- Declare "production ready"

**Ongoing**:
- Monitor effectiveness
- Collect metrics on breaking changes caught
- Iterate on false positive reduction
