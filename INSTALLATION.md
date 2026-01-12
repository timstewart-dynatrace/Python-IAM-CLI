# Installation Guide

This guide explains how to install Python-IAM-CLI on different platforms.

## Table of Contents

- [Quick Start](#quick-start)
- [System Requirements](#system-requirements)
- [Installation Methods](#installation-methods)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## Quick Start

### macOS / Linux (Recommended)
```bash
chmod +x install.sh
./install.sh
```

### Windows
```cmd
install.bat
```

## System Requirements

- **Python**: 3.10 or higher
- **pip**: Package installer for Python
- **OS**: macOS, Linux, or Windows

## Installation Methods

### Method 1: Automated Installation Scripts (Recommended)

The easiest way to install is using the provided installation scripts that handle all setup for you.

#### macOS / Linux

```bash
# Make the script executable
chmod +x install.sh

# Run the installation script
./install.sh
```

The script will:
1. Check Python version (3.10+)
2. Verify pip is installed
3. Offer installation options:
   - System-wide
   - User-wide
   - Virtual environment (recommended)
4. Install dependencies
5. Verify the installation

#### Windows

```cmd
# Run the installation script
install.bat
```

The script will guide you through the same steps on Windows.

### Method 2: Manual Installation with Virtual Environment (Linux/macOS)

If you prefer to set up manually:

```bash
# Clone or download the repository
git clone https://github.com/timstewart-dynatrace/Python-IAM-CLI.git
cd Python-IAM-CLI

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install the package
pip install -e .
```

### Method 3: Manual Installation System-Wide

```bash
# Clone or download the repository
git clone https://github.com/timstewart-dynatrace/Python-IAM-CLI.git
cd Python-IAM-CLI

# Install the package system-wide
pip install -e .
```

**Note**: On some systems, you may need `pip3` instead of `pip`, or use `sudo`.

### Method 4: User Installation (Linux/macOS)

```bash
# Clone or download the repository
git clone https://github.com/timstewart-dynatrace/Python-IAM-CLI.git
cd Python-IAM-CLI

# Install for current user only
pip install --user -e .
```

## Verification

After installation, verify everything works:

```bash
# Check the version
dtiam --version

# View help information
dtiam --help

# List available commands
dtiam
```

You should see output with available commands and options.

## Troubleshooting

### "python3: command not found"

Python is not installed or not in your PATH.

**Solution**: Install Python from [python.org](https://www.python.org/downloads/)

### "dtiam: command not found"

The CLI was installed but is not accessible in your PATH.

**Possible solutions**:
1. If you installed in a virtual environment, make sure it's activated:
   ```bash
   source ~/.python-iam-cli/venv/bin/activate
   ```

2. Add the installation path to your PATH:
   ```bash
   export PATH="$PATH:$HOME/.local/bin"
   ```

3. Try running with full path:
   ```bash
   python3 -m dtiam.cli --help
   ```

### Permission denied on install.sh

The script file needs execute permissions:

```bash
chmod +x install.sh
./install.sh
```

### ModuleNotFoundError or import errors

Make sure all dependencies are installed:

```bash
pip install --upgrade pip
pip install -e .
```

### Still having issues?

Check the [GitHub Issues](https://github.com/timstewart-dynatrace/Python-IAM-CLI/issues) or create a new issue with:
- Your OS and Python version (`python --version`)
- The exact error message
- Steps to reproduce

## Next Steps

After installation, check out:
- [Quick Start Guide](./QUICK_START.md) - Get started with basic commands
- [Commands Documentation](./COMMANDS.md) - Full command reference
- [Architecture Guide](./ARCHITECTURE.md) - Understand the project structure
