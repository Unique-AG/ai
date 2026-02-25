---
name: changelog-pyproject
description: Updates CHANGELOG.md and pyproject.toml version for releases. Use when the user wants to release changes, update the changelog, bump the version, or prepare a release.
---

# Changelog & pyproject Release Updates

Guides updating `CHANGELOG.md` and `pyproject.toml` when shipping changes.

## When to use

- User asks to "update the changelog", "bump the version", or "prepare a release"
- After implementing features, fixes, or tests that should be released
- When summarizing recent commits for a new version

## Workflow

### 1. Identify changes to document

Review recent commits or conversation context to list:

- **Added**: New features, functions, exports, tests
- **Changed**: Refactors, configuration changes
- **Fixed**: Bug fixes
- **Removed**: Deprecations, removals

### 2. Determine version bump

| Change type | Bump | Example |
|-------------|------|---------|
| Breaking changes, incompatible API | **Major** (x.0.0) | 1.47.4 → 2.0.0 |
| New features, backward compatible | **Minor** (0.x.0) | 1.47.4 → 1.48.0 |
| Bug fixes, docs, tests, config | **Patch** (0.0.x) | 1.47.4 → 1.47.5 |

This project typically uses **patch** for most releases.

### 3. CHANGELOG format

Follow [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Add new entry **at the top** (below the header), before the previous version:

```markdown
## [X.Y.Z] - YYYY-MM-DD
- Bullet point for each change
- Group by type if many: `### Added`, `### Changed`, `### Fixed`, `### Removed`
```

**Changelog style**

- Use past tense or imperative: "Add X", "Fix Y", "Move Z to..."
- Be concise but descriptive
- Include module/class/function names when relevant
- One logical change per bullet

### 4. pyproject.toml

Update the version string to match the new changelog entry:

```toml
[tool.poetry]
version = "X.Y.Z"
```

Locate under `[tool.poetry]` and change the `version` field only.

### 5. File locations

| Project | Changelog | pyproject |
|---------|-----------|-----------|
| unique_toolkit | `unique_toolkit/CHANGELOG.md` | `unique_toolkit/pyproject.toml` |
| unique_sdk | `unique_sdk/CHANGELOG.md` | `unique_sdk/pyproject.toml` |

Confirm paths exist before editing.

## Checklist

- [ ] CHANGELOG entry has correct version and date
- [ ] Changelog bullets describe all notable changes
- [ ] pyproject version matches CHANGELOG
- [ ] No other pyproject sections modified
