#!/bin/bash

###############################################################################
# Python-IAM-CLI Installation Script for macOS/Linux
# 
# This script installs the Python-IAM-CLI tool and its dependencies.
# 
# Usage:
#   chmod +x install.sh
#   ./install.sh
#
# Requirements:
#   - Python 3.10 or higher
#   - pip (Python package installer)
#   - Git (optional, for cloning the repository)
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check Python version
check_python() {
    print_info "Checking Python installation..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.10 or higher."
        echo "Visit: https://www.python.org/downloads/"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    REQUIRED_VERSION="3.10"
    
    if [[ $(echo -e "$PYTHON_VERSION\n$REQUIRED_VERSION" | sort -V | head -n1) != "$REQUIRED_VERSION" ]]; then
        print_error "Python $REQUIRED_VERSION or higher is required. Found: $PYTHON_VERSION"
        exit 1
    fi
    
    print_success "Python $PYTHON_VERSION found"
}

# Check pip
check_pip() {
    print_info "Checking pip installation..."
    
    if ! python3 -m pip --version &> /dev/null; then
        print_error "pip is not installed. Please install pip first."
        exit 1
    fi
    
    print_success "pip is installed"
}

# Get installation path
get_install_path() {
    if [ -z "$1" ]; then
        # Ask user for installation method
        echo ""
        echo "How would you like to install?"
        echo "1) System-wide (requires sudo)"
        echo "2) User-wide (--user flag)"
        echo "3) Virtual environment (recommended)"
        read -p "Enter choice (1-3, default: 3): " choice
        choice=${choice:-3}
        
        case $choice in
            1)
                INSTALL_FLAG="--break-system-packages"
                print_info "Installing system-wide"
                ;;
            2)
                INSTALL_FLAG="--user"
                print_info "Installing for current user"
                ;;
            3)
                setup_venv
                ;;
            *)
                print_error "Invalid choice. Using virtual environment."
                setup_venv
                ;;
        esac
    else
        INSTALL_FLAG="$1"
    fi
}

# Setup virtual environment
setup_venv() {
    VENV_PATH="${HOME}/.python-iam-cli/venv"
    print_info "Setting up virtual environment at $VENV_PATH..."
    
    mkdir -p "$(dirname "$VENV_PATH")"
    python3 -m venv "$VENV_PATH"
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    print_success "Virtual environment created and activated"
}

# Install the package
install_package() {
    print_header "Installing Python-IAM-CLI"
    
    # Get current directory
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    
    if [ ! -f "$SCRIPT_DIR/pyproject.toml" ]; then
        print_error "pyproject.toml not found. Are you running this from the project root?"
        exit 1
    fi
    
    print_info "Installing from $SCRIPT_DIR..."
    
    if [ -n "$INSTALL_FLAG" ]; then
        python3 -m pip install $INSTALL_FLAG -e "$SCRIPT_DIR"
    else
        python3 -m pip install -e "$SCRIPT_DIR"
    fi
    
    print_success "Python-IAM-CLI installed successfully"
}

# Verify installation
verify_installation() {
    print_header "Verifying Installation"
    
    if command -v dtiam &> /dev/null; then
        print_success "dtiam command is available"
        echo ""
        print_info "Getting version and help info..."
        dtiam --version || true
        echo ""
        dtiam --help | head -20
    else
        print_error "dtiam command not found. Please check your PATH or virtual environment activation."
    fi
}

# Main installation flow
main() {
    print_header "Python-IAM-CLI Installation"
    
    check_python
    check_pip
    get_install_path "$1"
    install_package
    verify_installation
    
    echo ""
    print_success "Installation complete!"
    echo ""
    print_info "Next steps:"
    
    if [ -n "$VENV_PATH" ]; then
        echo "1. Activate the virtual environment:"
        echo "   source $VENV_PATH/bin/activate"
        echo ""
        echo "2. Run dtiam commands:"
        echo "   dtiam --help"
    else
        echo "1. Run dtiam commands:"
        echo "   dtiam --help"
    fi
    
    echo ""
    echo "Documentation: https://github.com/timstewart-dynatrace/Python-IAM-CLI"
}

# Run main
main "$@"
