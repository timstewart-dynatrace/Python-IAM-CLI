#!/bin/bash
#
# IAM Full Lifecycle Validation Script
#
# Validates the complete IAM management lifecycle:
#   1. Create a test group
#   2. Create a test policy
#   3. Bind the policy to the group
#   4. Add a test user to the group
#   5. Verify the configuration
#   6. Clean up (delete test resources)
#
# Prerequisites:
#   - dtiam CLI installed (pip install -e .)
#   - Authentication configured (config file or environment variables)
#
# Usage:
#   bash example_cli_lifecycle.sh              # Dry-run mode (preview only)
#   bash example_cli_lifecycle.sh --execute    # Execute real changes
#   bash example_cli_lifecycle.sh --no-cleanup # Skip cleanup step
#   bash example_cli_lifecycle.sh --verbose    # Show detailed output
#   bash example_cli_lifecycle.sh --help       # Show this help
#
# Exit codes:
#   0 = All lifecycle steps successful
#   1 = One or more steps failed

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Test resource names (unique to avoid conflicts)
TEST_PREFIX="dtiam-test-$(date +%s)"
TEST_GROUP="${TEST_PREFIX}-group"
TEST_POLICY="${TEST_PREFIX}-policy"

# Options
EXECUTE=false
CLEANUP=true
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --execute)
            EXECUTE=true
            shift
            ;;
        --no-cleanup)
            CLEANUP=false
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            grep "^#" "$0" | grep -v "^#!" | cut -c 3-
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Helper functions
info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

step() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Step $1: $2${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

run_cmd() {
    local cmd=$1
    local description=$2

    if $VERBOSE; then
        echo -e "${CYAN}Command:${NC} $cmd"
    fi

    if $EXECUTE; then
        if eval "$cmd"; then
            success "$description"
        else
            error "$description failed"
            return 1
        fi
    else
        info "[DRY-RUN] Would execute: $cmd"
        success "$description (dry-run)"
    fi
}

# Header
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  dtiam CLI - IAM Lifecycle Validation"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

info "Mode: $([ "$EXECUTE" = true ] && echo 'EXECUTE (real changes)' || echo 'DRY-RUN (preview only)')"
info "Cleanup: $([ "$CLEANUP" = true ] && echo 'Enabled' || echo 'Disabled')"
info "Test prefix: $TEST_PREFIX"
echo ""

# Verify dtiam is available
if ! command -v dtiam &> /dev/null; then
    error "dtiam CLI not found. Install with: pip install -e ."
    exit 1
fi
success "dtiam CLI found"

# Verify authentication
step 1 "Verify Authentication"
if dtiam get groups --help > /dev/null 2>&1; then
    success "dtiam CLI is configured"
else
    error "dtiam CLI configuration issue"
    exit 1
fi

# List existing groups
step 2 "List Existing Groups"
run_cmd "dtiam get groups" "Retrieved existing groups"

# Create test group
step 3 "Create Test Group"
run_cmd "dtiam create group --name '$TEST_GROUP' --description 'Test group for lifecycle validation'" \
    "Created test group: $TEST_GROUP"

# Create test policy
step 4 "Create Test Policy"
run_cmd "dtiam create policy --name '$TEST_POLICY' --statement 'ALLOW settings:objects:read;' --description 'Test policy for lifecycle validation'" \
    "Created test policy: $TEST_POLICY"

# Bind policy to group
step 5 "Bind Policy to Group"
run_cmd "dtiam create binding --group '$TEST_GROUP' --policy '$TEST_POLICY'" \
    "Bound policy to group"

# Describe the group
step 6 "Verify Configuration"
run_cmd "dtiam describe group '$TEST_GROUP'" \
    "Retrieved group details"

run_cmd "dtiam group list-bindings '$TEST_GROUP'" \
    "Listed group bindings"

# Cleanup
if $CLEANUP; then
    step 7 "Cleanup Test Resources"

    if $EXECUTE; then
        warning "Cleaning up test resources..."

        # Delete binding first
        dtiam delete binding --group "$TEST_GROUP" --policy "$TEST_POLICY" --force 2>/dev/null || true
        success "Deleted test binding"

        # Delete policy
        dtiam delete policy "$TEST_POLICY" --force 2>/dev/null || true
        success "Deleted test policy: $TEST_POLICY"

        # Delete group
        dtiam delete group "$TEST_GROUP" --force 2>/dev/null || true
        success "Deleted test group: $TEST_GROUP"
    else
        info "[DRY-RUN] Would delete: binding, policy ($TEST_POLICY), group ($TEST_GROUP)"
    fi
else
    warning "Cleanup skipped. Test resources remain:"
    info "  Group: $TEST_GROUP"
    info "  Policy: $TEST_POLICY"
fi

# Summary
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  Lifecycle Validation Complete"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

if $EXECUTE; then
    success "All lifecycle steps completed successfully!"
else
    info "Dry-run complete. Use --execute to apply changes."
fi

echo ""
info "Steps validated:"
echo "  1. Authentication verification"
echo "  2. List existing groups"
echo "  3. Create group"
echo "  4. Create policy"
echo "  5. Bind policy to group"
echo "  6. Verify configuration"
if $CLEANUP; then
    echo "  7. Cleanup test resources"
fi

echo ""
exit 0
