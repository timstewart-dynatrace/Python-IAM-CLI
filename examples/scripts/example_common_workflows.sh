#!/bin/bash
#
# Common dtiam CLI Workflows
#
# This script demonstrates common IAM management workflows.
# Run individual sections or use as a reference.
#
# Usage:
#   bash example_common_workflows.sh           # Show all workflows
#   bash example_common_workflows.sh groups    # Group management workflows
#   bash example_common_workflows.sh users     # User management workflows
#   bash example_common_workflows.sh policies  # Policy management workflows
#   bash example_common_workflows.sh analyze   # Analysis workflows

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

show_section() {
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

show_command() {
    echo -e "${GREEN}$${NC} $1"
    echo ""
}

show_note() {
    echo -e "${YELLOW}Note:${NC} $1"
    echo ""
}

# ============================================================================
# GROUP MANAGEMENT WORKFLOWS
# ============================================================================
show_groups() {
    show_section "GROUP MANAGEMENT WORKFLOWS"

    echo "# List all groups"
    show_command "dtiam get groups"

    echo "# Get a specific group by name"
    show_command "dtiam get groups 'DevOps Team'"

    echo "# Describe group with full details"
    show_command "dtiam describe group 'DevOps Team'"

    echo "# Create a new group"
    show_command "dtiam create group --name 'New Team' --description 'New team description'"

    echo "# List group members"
    show_command "dtiam group list-members 'DevOps Team'"

    echo "# List group policy bindings"
    show_command "dtiam group list-bindings 'DevOps Team'"

    echo "# Clone a group (with policies)"
    show_command "dtiam group clone 'Source Group' --name 'Cloned Group'"

    echo "# Clone a group (with members and policies)"
    show_command "dtiam group clone 'Source Group' --name 'Cloned Group' --include-members"

    echo "# Create group with policy in one command"
    show_command "dtiam group setup --name 'Quick Team' --policy 'Standard User'"

    echo "# Delete a group"
    show_command "dtiam delete group 'Old Team' --force"
}

# ============================================================================
# USER MANAGEMENT WORKFLOWS
# ============================================================================
show_users() {
    show_section "USER MANAGEMENT WORKFLOWS"

    echo "# List all users"
    show_command "dtiam get users"

    echo "# Get user by email"
    show_command "dtiam get users user@example.com"

    echo "# Show detailed user info"
    show_command "dtiam describe user user@example.com"

    echo "# Create a new user"
    show_command "dtiam user create --email newuser@example.com --first-name John --last-name Doe"

    echo "# Create user and add to groups"
    show_command "dtiam user create --email newuser@example.com --groups 'DevOps,Platform'"

    echo "# Add user to a group"
    show_command "dtiam user add-to-group --user user@example.com --group 'DevOps Team'"

    echo "# Remove user from a group"
    show_command "dtiam user remove-from-group --user user@example.com --group 'Old Team'"

    echo "# List user's groups"
    show_command "dtiam user list-groups user@example.com"

    echo "# Replace all user's groups (careful!)"
    show_command "dtiam user replace-groups --user user@example.com --groups 'NewTeam1,NewTeam2'"

    echo "# Bulk add user to multiple groups"
    show_command "dtiam user bulk-add-groups --user user@example.com --groups 'Team1,Team2,Team3'"

    echo "# Delete a user"
    show_command "dtiam user delete user@example.com --force"
}

# ============================================================================
# POLICY MANAGEMENT WORKFLOWS
# ============================================================================
show_policies() {
    show_section "POLICY MANAGEMENT WORKFLOWS"

    echo "# List all policies (account level)"
    show_command "dtiam get policies"

    echo "# List global policies"
    show_command "dtiam get policies --level global"

    echo "# Get policy by name"
    show_command "dtiam get policies 'Admin User'"

    echo "# Describe policy with permissions"
    show_command "dtiam describe policy 'Admin User'"

    echo "# Create a simple policy"
    show_command "dtiam create policy --name 'viewer' --statement 'ALLOW settings:objects:read;'"

    echo "# Create policy with multiple permissions"
    show_command "dtiam create policy --name 'devops' --statement 'ALLOW settings:objects:read, settings:objects:write, storage:metrics:read;'"

    echo "# Create policy with conditions"
    show_command 'dtiam create policy --name "alerting-only" --statement '\''ALLOW settings:objects:read, settings:objects:write WHERE settings:schemaId STARTS WITH "builtin:alerting";'\'''

    echo "# Export policy as template"
    show_command "dtiam export policy 'My Policy' --as-template -o my-policy-template.yaml"

    echo "# Delete a policy"
    show_command "dtiam delete policy 'Old Policy' --force"
}

# ============================================================================
# BINDING MANAGEMENT WORKFLOWS
# ============================================================================
show_bindings() {
    show_section "BINDING MANAGEMENT WORKFLOWS"

    echo "# List all bindings"
    show_command "dtiam get bindings"

    echo "# Create a binding (policy to group)"
    show_command "dtiam create binding --group 'DevOps Team' --policy 'Pro User'"

    echo "# Create binding with boundary restriction"
    show_command "dtiam create binding --group 'DevOps Team' --policy 'Admin User' --boundary 'prod-boundary'"

    echo "# Delete a binding"
    show_command "dtiam delete binding --group 'DevOps Team' --policy 'Old Policy' --force"
}

# ============================================================================
# BOUNDARY MANAGEMENT WORKFLOWS
# ============================================================================
show_boundaries() {
    show_section "BOUNDARY MANAGEMENT WORKFLOWS"

    echo "# List all boundaries"
    show_command "dtiam get boundaries"

    echo "# Create a zone-based boundary"
    show_command "dtiam create boundary --name 'prod-boundary' --zones 'Production,Staging'"

    echo "# Create boundary with custom query"
    show_command 'dtiam create boundary --name "custom-boundary" --query "management-zone IN (\"Zone1\", \"Zone2\")"'

    echo "# Attach boundary to existing binding"
    show_command "dtiam boundary attach --group 'DevOps' --policy 'Admin User' --boundary 'prod-boundary'"

    echo "# Detach boundary from binding"
    show_command "dtiam boundary detach --group 'DevOps' --policy 'Admin User' --boundary 'prod-boundary'"

    echo "# List bindings using a boundary"
    show_command "dtiam boundary list-attached 'prod-boundary'"

    echo "# Delete a boundary"
    show_command "dtiam delete boundary 'old-boundary' --force"
}

# ============================================================================
# ANALYSIS WORKFLOWS
# ============================================================================
show_analyze() {
    show_section "ANALYSIS WORKFLOWS"

    echo "# Analyze user's effective permissions (calculated)"
    show_command "dtiam analyze user-permissions user@example.com"

    echo "# Get effective permissions from Dynatrace API"
    show_command "dtiam analyze effective-user user@example.com"

    echo "# Analyze group permissions"
    show_command "dtiam analyze group-permissions 'DevOps Team'"

    echo "# Get effective permissions for group from API"
    show_command "dtiam analyze effective-group 'DevOps Team'"

    echo "# Analyze a specific policy"
    show_command "dtiam analyze policy 'My Policy'"

    echo "# Generate permissions matrix"
    show_command "dtiam analyze permissions-matrix"

    echo "# Export permissions matrix to CSV"
    show_command "dtiam analyze permissions-matrix --export permissions.csv"

    echo "# Analyze least-privilege compliance"
    show_command "dtiam analyze least-privilege"

    echo "# Export least-privilege findings"
    show_command "dtiam analyze least-privilege --export findings.json"
}

# ============================================================================
# BULK OPERATIONS WORKFLOWS
# ============================================================================
show_bulk() {
    show_section "BULK OPERATIONS WORKFLOWS"

    echo "# Add multiple users to a group from CSV"
    show_command "dtiam bulk add-users-to-group --file users.csv --group 'DevOps Team'"

    echo "# Remove multiple users from a group"
    show_command "dtiam bulk remove-users-from-group --file users.csv --group 'Old Team' --force"

    echo "# Create multiple groups from YAML"
    show_command "dtiam bulk create-groups --file groups.yaml"

    echo "# Create multiple bindings from YAML"
    show_command "dtiam bulk create-bindings --file bindings.yaml"

    echo "# Export group members to CSV"
    show_command "dtiam bulk export-group-members --group 'DevOps Team' -o members.csv"
}

# ============================================================================
# EXPORT WORKFLOWS
# ============================================================================
show_export() {
    show_section "EXPORT WORKFLOWS"

    echo "# Export all IAM resources"
    show_command "dtiam export all -o ./backup"

    echo "# Export specific resources"
    show_command "dtiam export all --include groups,policies -o ./backup"

    echo "# Export in JSON format"
    show_command "dtiam export all -f json -o ./backup"

    echo "# Export with detailed data"
    show_command "dtiam export all --detailed -o ./backup"

    echo "# Export single group"
    show_command "dtiam export group 'DevOps Team' -o devops-group.yaml"

    echo "# Export policy as template"
    show_command "dtiam export policy 'My Policy' --as-template -o policy-template.yaml"
}

# ============================================================================
# SERVICE USER WORKFLOWS
# ============================================================================
show_service_users() {
    show_section "SERVICE USER (OAUTH CLIENT) WORKFLOWS"

    echo "# List all service users"
    show_command "dtiam get service-users"

    echo "# Create a service user"
    show_command "dtiam create service-user --name 'CI Pipeline'"
    show_note "Save the client secret immediately - it cannot be retrieved later!"

    echo "# Create service user and save credentials"
    show_command "dtiam create service-user --name 'CI Pipeline' --save-credentials creds.json"

    echo "# Create service user with group membership"
    show_command "dtiam create service-user --name 'CI Pipeline' --groups 'Automation,DevOps'"

    echo "# Add service user to group"
    show_command "dtiam service-user add-to-group --user 'CI Pipeline' --group 'DevOps'"

    echo "# List service user's groups"
    show_command "dtiam service-user list-groups 'CI Pipeline'"

    echo "# Delete service user"
    show_command "dtiam delete service-user 'CI Pipeline' --force"
}

# ============================================================================
# MAIN
# ============================================================================

case "${1:-all}" in
    groups)
        show_groups
        ;;
    users)
        show_users
        ;;
    policies)
        show_policies
        ;;
    bindings)
        show_bindings
        ;;
    boundaries)
        show_boundaries
        ;;
    analyze)
        show_analyze
        ;;
    bulk)
        show_bulk
        ;;
    export)
        show_export
        ;;
    service-users)
        show_service_users
        ;;
    all)
        show_groups
        show_users
        show_policies
        show_bindings
        show_boundaries
        show_analyze
        show_bulk
        show_export
        show_service_users
        ;;
    *)
        echo "Usage: $0 [groups|users|policies|bindings|boundaries|analyze|bulk|export|service-users|all]"
        exit 1
        ;;
esac

echo ""
echo -e "${CYAN}For more information, see:${NC}"
echo "  dtiam --help"
echo "  dtiam <command> --help"
echo "  docs/COMMANDS.md"
echo ""
