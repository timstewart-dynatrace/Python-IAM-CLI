# Development Workflow

This document defines the mandatory development workflow for the dtiam project.

## Branch Strategy

### Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Features | `feature/descriptive-name` | `feature/add-apps-resource` |
| Bug fixes | `fix/descriptive-name` | `fix/group-get-fallback` |
| Documentation | `docs/descriptive-name` | `docs/update-commands` |
| Chores | `chore/descriptive-name` | `chore/bump-version` |

### Rules

1. **NEVER commit directly to main**
   - All changes must go through feature branches
   - Only exception: critical hotfixes with approval

2. **Keep branches focused**
   - One feature/fix per branch
   - Small, reviewable changes

## Workflow Steps

### 1. Create Feature Branch

```bash
git checkout main
git pull
git checkout -b feature/my-feature
```

### 2. Develop and Test

```bash
# Make changes
# ...

# Run tests
pytest tests/ -v

# Run type checking
mypy src/dtiam

# Run linting
ruff check src/dtiam
```

### 3. Commit Changes

Use conventional commit messages:

```bash
git add <files>
git commit -m "feat: add new feature description"
```

**Commit Types:**
| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no code change |
| `refactor` | Code restructuring |
| `test` | Adding tests |
| `chore` | Maintenance tasks |

### 4. Update Documentation

**MANDATORY before merge:**

- [ ] [CLAUDE.md](../../../CLAUDE.md) - Project structure/patterns
- [ ] [docs/COMMANDS.md](../../../docs/COMMANDS.md) - Command reference
- [ ] [README.md](../../../README.md) - Quick start/features
- [ ] Code docstrings for new functions

### 5. Version Bump

For features and fixes, increment version:

```bash
# Edit pyproject.toml and src/dtiam/__init__.py
# Use semantic versioning: MAJOR.MINOR.PATCH

git add pyproject.toml src/dtiam/__init__.py
git commit -m "chore: bump version to X.Y.Z"
```

### 6. Update CHANGELOG

Add entry to CHANGELOG.md:

```markdown
## [Unreleased]

### Added
- New feature description

### Fixed
- Bug fix description
```

### 7. Push and Merge

```bash
# Push feature branch
git push -u origin feature/my-feature

# Merge to main
git checkout main
git merge feature/my-feature --no-ff
git push
```

## Version Management

### Semantic Versioning

**Format:** `MAJOR.MINOR.PATCH`

| Change Type | Version Bump | Example |
|-------------|--------------|---------|
| Breaking changes | MAJOR | 3.0.0 → 4.0.0 |
| New features | MINOR | 3.0.0 → 3.1.0 |
| Bug fixes | PATCH | 3.0.0 → 3.0.1 |

### Version Locations

Update version in **both** files:

1. `pyproject.toml` (line 7)
2. `src/dtiam/__init__.py` (line 3)
3. `src/dtiam/client.py` User-Agent string

### Version Checklist

- [ ] Versions match in all files
- [ ] Correct bump type (MAJOR/MINOR/PATCH)
- [ ] CHANGELOG updated
- [ ] Version commit in feature branch

## CHANGELOG Format

Follow [Keep a Changelog](https://keepachangelog.com/):

```markdown
## [Unreleased]

### Added
- New features

### Changed
- Changes to existing features

### Fixed
- Bug fixes

### Removed
- Removed features

## [3.12.0] - 2025-01-22

### Added
- Platform token management
- Custom OAuth scopes support
```

## Pre-Merge Checklist

Before merging to main:

- [ ] All tests pass: `pytest tests/ -v`
- [ ] Type checking passes: `mypy src/dtiam`
- [ ] Linting passes: `ruff check src/dtiam`
- [ ] Documentation updated
- [ ] Version bumped
- [ ] CHANGELOG updated
- [ ] Feature branch pushed
- [ ] Merge uses `--no-ff`

## Creating Releases

After merging version bump:

```bash
# Create tag
git tag -a v3.12.0 -m "Release version 3.12.0"
git push origin v3.12.0

# Create GitHub release
gh release create v3.12.0 --title "v3.12.0" --notes-from-tag
```

## Quick Reference

```bash
# Full workflow
git checkout main && git pull
git checkout -b feature/my-feature
# ... make changes ...
pytest tests/ -v
# ... update docs ...
# ... bump version ...
git add . && git commit -m "feat: description"
git push -u origin feature/my-feature
git checkout main
git merge feature/my-feature --no-ff
git push
```
