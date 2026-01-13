# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

No unreleased changes yet.

## [3.4.0] - 2026-01-13

### Added
- Multi-level querying for `get policies` command
  - Now queries all levels by default (account, global, and environments)
  - Added `--level` option to filter by level (account, global, environment, or specific env ID)
- Multi-level querying for `get bindings` command
  - Now queries all levels by default (account, global, and environments)
  - Added `--level` option to filter by level

### Fixed
- Fixed /repo/ API endpoint paths (policies, bindings, boundaries)
  - These endpoints use `/iam/v1/repo/` not `/iam/v1/accounts/{uuid}/repo/`
- Fixed `zone_columns()` to return Column objects instead of tuples

### Changed
- User-Agent bumped to dtiam/3.4.0

## [3.3.0] - 2026-01-13

### Added
- Partial credential update support for `config set-credentials`
  - Update just `--environment-token` without re-entering all credentials
  - Update `--environment-url`, `--client-id`, or `--client-secret` individually
  - Only prompts for required fields when creating new credentials
- Store `environment-url` and `environment-token` in credential configuration
- Store `environment-url` in context configuration

### Changed
- `config set-credentials` now supports partial updates for existing credentials
- Credential model extended with `environment-url` and `environment-token` fields
- Context model extended with `environment-url` field
- User-Agent bumped to dtiam/3.3.0

## [3.2.0] - 2025-01-13

### Added
- Optional environment token support for management zones (legacy feature)
  - `DTIAM_ENVIRONMENT_TOKEN` environment variable for environment-level API access
  - Auto-detection of environment API URLs (.live.dynatrace.com, .apps.dynatrace.com)
  - Enables management zone operations with environment-level API tokens

### Changed
- Updated Client class to support optional environment_token parameter
- User-Agent bumped to dtiam/3.2.0

### Documentation
- Added `DTIAM_ENVIRONMENT_TOKEN` documentation to config.py and .env.example

## [3.1.0] - 2025-01-13

### Added
- `get apps` command for listing Dynatrace Apps from App Engine Registry
  - Supports `--environment` flag or `DTIAM_ENVIRONMENT_URL` environment variable
  - `--ids` flag to output only app IDs for use in policy statements
  - App IDs can be used in policies: `shared:app-id = '{app.id}'`
- `bulk create-groups-with-policies` command for integrated group/policy/binding creation
  - Creates groups, boundaries, and policy bindings in one operation
  - Supports CSV input with columns: group_name, policy_name, level, level_id, management_zones, boundary_name, description
  - Idempotent operation (skips existing resources)
  - Example file: `examples/bulk/sample_bulk_groups.csv`
- Development workflow documentation in CLAUDE.md
  - Mandatory branching requirements (no direct commits to main)
  - Mandatory documentation checklist before merge
  - Mandatory version increment requirements
  - Semantic versioning guidelines with examples

### Changed
- Enhanced `.gitignore` with better Python/IDE exclusions
- Improved boundary handling in `BoundaryHandler`

### Documentation
- Added comprehensive command reference for `get apps` in docs/COMMANDS.md
- Added bulk create-groups-with-policies documentation in docs/COMMANDS.md
- Updated README.md with new resources and bulk operations
- Updated examples/README.md with new sample files
- Added App Engine Registry API endpoints to CLAUDE.md
- Added mandatory development workflow to CLAUDE.md
- Added version management requirements to CLAUDE.md

### Tests
- Added new test coverage in `tests/test_resources.py`

## [3.0.0] - 2024-XX-XX

### Initial Release
- kubectl-inspired CLI for Dynatrace IAM management
- Resource management: groups, users, policies, bindings, boundaries, environments
- Service user (OAuth client) management
- Account limits and subscriptions
- Multi-context configuration support
- OAuth2 and bearer token authentication
- Output formats: table, json, yaml, csv, wide
- Bulk operations for users, groups, and bindings
- Template system with Jinja2-style variables
- Permissions analysis and effective permissions
- Management zones (legacy - to be removed)
- Comprehensive documentation and examples
- Automated installation scripts for macOS/Linux/Windows

[Unreleased]: https://github.com/timstewart-dynatrace/Python-IAM-CLI/compare/v3.4.0...HEAD
[3.4.0]: https://github.com/timstewart-dynatrace/Python-IAM-CLI/compare/v3.3.0...v3.4.0
[3.3.0]: https://github.com/timstewart-dynatrace/Python-IAM-CLI/compare/v3.2.0...v3.3.0
[3.2.0]: https://github.com/timstewart-dynatrace/Python-IAM-CLI/compare/v3.1.0...v3.2.0
[3.1.0]: https://github.com/timstewart-dynatrace/Python-IAM-CLI/compare/v3.0.0...v3.1.0
[3.0.0]: https://github.com/timstewart-dynatrace/Python-IAM-CLI/releases/tag/v3.0.0
