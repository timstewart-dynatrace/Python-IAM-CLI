# Policy Examples

This directory contains example IAM policy configurations demonstrating common permission patterns.

> **⚠️ DISCLAIMER**: This tool is provided "as-is" without warranty. **Use at your own risk.**  This tool is an independent, community-driven project and **not produced, endorsed, or supported by Dynatrace**. The authors assume no liability for any issues arising from its use.

## Available Policies

### Read-Only Policies

| File | Description | Use Case |
|------|-------------|----------|
| `viewer-policy.yaml` | Read-only access to settings, metrics, logs | Stakeholders, auditors |

### Operational Policies

| File | Description | Use Case |
|------|-------------|----------|
| `devops-policy.yaml` | Settings, automation, and monitoring access | DevOps/Platform teams |
| `slo-manager.yaml` | SLO management with supporting data | SRE teams |
| `settings-writer.yaml` | Full settings read/write access | Configuration managers |

### Restricted Policies

| File | Description | Use Case |
|------|-------------|----------|
| `alerting-only.yaml` | Alerting settings only (schema-restricted) | Alert managers |

## Policy Statement Syntax

Dynatrace IAM uses a declarative policy language:

```
ALLOW <service>:<resource>:<action> [WHERE <condition>];
```

### Common Services

| Service | Description |
|---------|-------------|
| `settings:objects` | Configuration settings |
| `storage:metrics` | Metrics data |
| `storage:logs` | Log data |
| `storage:events` | Events data |
| `storage:spans` | Distributed traces |
| `document:documents` | Dashboards and documents |
| `slo:slos` | Service Level Objectives |
| `automation:workflows` | Workflows |

### Common Actions

| Action | Description |
|--------|-------------|
| `read` | View data |
| `write` | Create and modify |
| `delete` | Remove data |
| `run` | Execute (workflows, apps) |

### Conditions

Restrict permissions with conditions:

```
# Restrict to specific schema
WHERE settings:schemaId STARTS WITH "builtin:alerting"

# Restrict to management zones
WHERE management-zone IN ("Zone1", "Zone2")
```

## Usage

### Create from Example

```bash
# View the policy
cat examples/policies/viewer-policy.yaml

# Create using the statement
dtiam create policy --name "viewer-policy" \
  --description "Read-only access" \
  --statement "ALLOW settings:objects:read, storage:metrics:read, storage:logs:read;"
```

### Built-in Policies

Dynatrace provides built-in policies that don't need to be created:

| Policy | Description |
|--------|-------------|
| `Standard User` | Basic access with app execution |
| `Pro User` | Extended access with settings write |
| `Admin User` | Full administrative access |

```bash
# Use built-in policy directly
dtiam create binding --group "My Team" --policy "Standard User"
```

## Best Practices

1. **Least Privilege**: Start with minimal permissions, add as needed
2. **Use Boundaries**: Restrict write access to specific zones
3. **Audit Regularly**: Review policies with `dtiam analyze least-privilege`
4. **Document Purpose**: Use clear names and descriptions
5. **Test First**: Use `--dry-run` to preview changes

## Examples

### Create Read-Only Policy

```bash
dtiam create policy --name "viewer" \
  --description "Read-only access" \
  --statement "ALLOW settings:objects:read, storage:metrics:read, document:documents:read;"
```

### Create Schema-Restricted Policy

```bash
dtiam create policy --name "alerting-manager" \
  --description "Alerting settings only" \
  --statement 'ALLOW settings:objects:read, settings:objects:write WHERE settings:schemaId STARTS WITH "builtin:alerting";'
```

### Create Full DevOps Policy

```bash
dtiam create policy --name "devops-full" \
  --description "Full DevOps access" \
  --statement "ALLOW settings:objects:read, settings:objects:write, storage:metrics:read, storage:logs:read, automation:workflows:read, automation:workflows:run;"
```

## Reference

- [Dynatrace IAM Policy Reference](https://docs.dynatrace.com/docs/manage/identity-access-management/permission-management/manage-user-permissions-policies/advanced/iam-policystatements)
- [Policy Statement Syntax](https://docs.dynatrace.com/docs/manage/identity-access-management/permission-management/manage-user-permissions-policies/iam-policystatement-syntax)
- [dtiam Commands Reference](../../docs/COMMANDS.md)
