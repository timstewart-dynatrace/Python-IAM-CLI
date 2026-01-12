# GitHub Releases Distribution Guide

This guide explains how to use GitHub Releases to distribute Python-IAM-CLI to users.

## Overview

GitHub Releases provides a way to distribute your software with version control and release notes. Users can download source code, installation scripts, and future pre-built executables directly from your repository.

## How Users Install from a Release

### Method 1: Download and Run Installation Script (Easiest)

1. Go to your GitHub repository: https://github.com/timstewart-dynatrace/Python-IAM-CLI/releases
2. Click on the latest release
3. Download the `.zip` or `.tar.gz` source code archive
4. Extract the archive
5. Run the installation script:
   - **macOS/Linux**: `./install.sh`
   - **Windows**: `install.bat`

### Method 2: Clone from GitHub

```bash
# Clone the repository at a specific release tag
git clone --branch v3.0.0 https://github.com/timstewart-dynatrace/Python-IAM-CLI.git
cd Python-IAM-CLI
./install.sh  # macOS/Linux
# or
install.bat   # Windows
```

### Method 3: Download Source and Install Manually

1. Download the source code from a release
2. Extract it
3. Run: `pip install -e .`

## How to Create a Release on GitHub

### Step 1: Create a Git Tag

When you're ready to release a new version:

```bash
# Update version in pyproject.toml first
# Then create and push a tag
git tag -a v3.0.0 -m "Release version 3.0.0"
git push origin v3.0.0
```

### Step 2: Create Release on GitHub

**Option A: Using GitHub Web Interface**

1. Go to https://github.com/timstewart-dynatrace/Python-IAM-CLI/releases
2. Click "Draft a new release"
3. Select the tag you just created
4. Enter release title: `v3.0.0`
5. Fill in release notes (see template below)
6. Attach release assets if any (future: executables)
7. Click "Publish release"

**Option B: Using GitHub CLI**

```bash
# If you don't have gh CLI, install it first:
# macOS: brew install gh
# Linux: https://github.com/cli/cli/releases
# Windows: choco install gh

# Create and publish a release
gh release create v3.0.0 \
  --title "v3.0.0" \
  --notes "Release notes here" \
  --draft=false
```

### Step 3: Release Notes Template

When creating a release, use this template for clear, professional notes:

```markdown
## What's New

### Features
- Feature 1
- Feature 2

### Improvements
- Improvement 1
- Improvement 2

### Bug Fixes
- Bug fix 1
- Bug fix 2

### Requirements
- Python 3.10+
- See [Installation Guide](https://github.com/timstewart-dynatrace/Python-IAM-CLI/blob/main/INSTALLATION.md)

## Installation

### Quick Start
```bash
# Download the source code from this release
# Extract it
./install.sh  # macOS/Linux
install.bat   # Windows
```

### Manual Installation
```bash
pip install -e .
```

See [INSTALLATION.md](https://github.com/timstewart-dynatrace/Python-IAM-CLI/blob/main/INSTALLATION.md) for detailed instructions.

## Changes

See the [commit log](https://github.com/timstewart-dynatrace/Python-IAM-CLI/compare/v2.9.0...v3.0.0)
```

## Versioning Scheme

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., 3.0.0)
  - **MAJOR**: Breaking changes
  - **MINOR**: New features (backward compatible)
  - **PATCH**: Bug fixes

### Examples
- `v3.0.0` - Major release with new features
- `v3.1.0` - Minor release with new features
- `v3.1.1` - Patch release with bug fixes
- `v3.0.0-beta.1` - Beta release

## Directory Structure in Releases

When you create a release on GitHub, it automatically provides:

```
Python-IAM-CLI
├── Python-IAM-CLI-v3.0.0.zip       (source code)
├── Python-IAM-CLI-v3.0.0.tar.gz    (source code)
└── [Release notes]
```

Users can download either format and run the installation scripts.

## Future: Adding Pre-Built Executables

Once you set up PyInstaller or similar tools, you can attach binary executables:

```
Python-IAM-CLI-v3.0.0.dmg          # macOS
Python-IAM-CLI-v3.0.0.exe          # Windows
python-iam-cli-v3.0.0.tar.gz       # Linux
```

This is done by:
1. Building the executables locally
2. Uploading them as release assets

See the PyInstaller guide for more details.

## Best Practices

✅ **Do:**
- Create a release for each version
- Use semantic versioning
- Write clear release notes with what changed
- Include breaking changes prominently
- Update the version in `pyproject.toml` before creating a tag
- Use meaningful commit messages

❌ **Don't:**
- Skip releases for minor updates
- Create releases without version tags
- Put sensitive information in release notes
- Upload unnecessarily large binaries

## Updating Installation Instructions

When you have a stable release, you can point users to it:

```bash
# Clone a specific release version
git clone --branch v3.0.0 https://github.com/timstewart-dynatrace/Python-IAM-CLI.git
```

## Troubleshooting

### Release not showing up
- Make sure the tag was pushed: `git push origin --tags`
- Wait a few seconds for GitHub to process it
- Refresh the releases page

### Can't create a release
- Make sure you have push access to the repository
- Ensure the tag exists: `git tag -l`

### Installation fails from a release
- Users should check [INSTALLATION.md](./INSTALLATION.md)
- Make sure `install.sh` is executable: `chmod +x install.sh`
- Ensure Python 3.10+ is installed

## Next Steps

1. **Commit and push** your code:
   ```bash
   git add .
   git commit -m "Your message"
   git push
   ```

2. **Create a version tag**:
   ```bash
   git tag -a v3.0.0 -m "Release version 3.0.0"
   git push origin v3.0.0
   ```

3. **Create a release** on GitHub web interface or CLI

4. **Share the link** with users: `https://github.com/timstewart-dynatrace/Python-IAM-CLI/releases`

Users can now download and install your tool directly from GitHub!
