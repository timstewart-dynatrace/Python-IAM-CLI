"""Permissions analysis utilities.

Provides effective permissions calculation, permissions matrix generation,
and direct API calls for effective permissions resolution.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Literal

from dtiam.client import Client, APIError


# Common permission patterns in Dynatrace IAM
PERMISSION_PATTERNS = {
    "settings:objects:read": "Read settings objects",
    "settings:objects:write": "Write settings objects",
    "settings:schemas:read": "Read settings schemas",
    "environment:roles:manage": "Manage environment roles",
    "account:users:read": "Read account users",
    "account:users:write": "Write account users",
    "account:groups:read": "Read account groups",
    "account:groups:write": "Write account groups",
    "account:policies:read": "Read account policies",
    "account:policies:write": "Write account policies",
}


def parse_statement_query(statement: str) -> list[dict[str, Any]]:
    """Parse a policy statement query into structured permissions.

    Args:
        statement: Policy statement query string

    Returns:
        List of permission dicts with action, resource, conditions
    """
    permissions = []

    # Split by semicolons for multiple statements
    statements = [s.strip() for s in statement.split(";") if s.strip()]

    for stmt in statements:
        # Parse ALLOW/DENY statements
        match = re.match(
            r"(ALLOW|DENY)\s+([^\s]+(?:\s*,\s*[^\s]+)*)\s*(?:WHERE\s+(.+))?",
            stmt,
            re.IGNORECASE,
        )
        if match:
            effect = match.group(1).upper()
            actions_str = match.group(2)
            conditions = match.group(3)

            # Parse actions
            actions = [a.strip() for a in actions_str.split(",")]

            for action in actions:
                perm = {
                    "effect": effect,
                    "action": action,
                    "description": PERMISSION_PATTERNS.get(action, action),
                }
                if conditions:
                    perm["conditions"] = conditions
                permissions.append(perm)

    return permissions


class PermissionsCalculator:
    """Calculates effective permissions for users and groups."""

    def __init__(self, client: Client):
        self.client = client

    def get_user_effective_permissions(self, user_id: str) -> dict[str, Any]:
        """Calculate effective permissions for a user.

        Args:
            user_id: User UID or email

        Returns:
            Dictionary with permissions breakdown
        """
        from dtiam.resources.users import UserHandler
        from dtiam.resources.groups import GroupHandler
        from dtiam.resources.policies import PolicyHandler
        from dtiam.resources.bindings import BindingHandler

        user_handler = UserHandler(self.client)
        group_handler = GroupHandler(self.client)
        policy_handler = PolicyHandler(
            self.client, level_type="account", level_id=self.client.account_uuid
        )
        binding_handler = BindingHandler(self.client)

        # Resolve user
        if "@" in user_id:
            user = user_handler.get_by_email(user_id)
        else:
            user = user_handler.get(user_id)

        if not user:
            return {"error": f"User not found: {user_id}"}

        user_uid = user.get("uid", user_id)
        user_email = user.get("email", user_id)

        # Get user's groups
        groups = user_handler.get_groups(user_uid)

        # Collect all policy bindings from all groups
        all_bindings = []
        group_permissions = []

        for group in groups:
            group_id = group.get("uuid", "")
            group_name = group.get("name", "")

            # Get bindings for this group
            bindings = binding_handler.get_for_group(group_id)

            for binding in bindings:
                policy_uuid = binding.get("policyUuid", "")
                policy = policy_handler.get(policy_uuid)

                if policy:
                    statement = policy.get("statementQuery", "")
                    permissions = parse_statement_query(statement)

                    binding_info = {
                        "group_uuid": group_id,
                        "group_name": group_name,
                        "policy_uuid": policy_uuid,
                        "policy_name": policy.get("name", ""),
                        "permissions": permissions,
                        "boundary": binding.get("boundaryUuid"),
                    }
                    all_bindings.append(binding_info)

                    for perm in permissions:
                        group_permissions.append({
                            "source_group": group_name,
                            "source_policy": policy.get("name", ""),
                            **perm,
                        })

        # Aggregate unique permissions
        unique_permissions = {}
        for perm in group_permissions:
            key = f"{perm['effect']}:{perm['action']}"
            if key not in unique_permissions:
                unique_permissions[key] = {
                    "effect": perm["effect"],
                    "action": perm["action"],
                    "description": perm["description"],
                    "sources": [],
                }
            unique_permissions[key]["sources"].append({
                "group": perm["source_group"],
                "policy": perm["source_policy"],
            })

        return {
            "user": {
                "uid": user_uid,
                "email": user_email,
            },
            "groups": [{"uuid": g.get("uuid"), "name": g.get("name")} for g in groups],
            "group_count": len(groups),
            "bindings": all_bindings,
            "binding_count": len(all_bindings),
            "effective_permissions": list(unique_permissions.values()),
            "permission_count": len(unique_permissions),
        }

    def get_group_effective_permissions(self, group_id: str) -> dict[str, Any]:
        """Calculate effective permissions for a group.

        Args:
            group_id: Group UUID or name

        Returns:
            Dictionary with permissions breakdown
        """
        from dtiam.resources.groups import GroupHandler
        from dtiam.resources.policies import PolicyHandler
        from dtiam.resources.bindings import BindingHandler

        group_handler = GroupHandler(self.client)
        policy_handler = PolicyHandler(
            self.client, level_type="account", level_id=self.client.account_uuid
        )
        binding_handler = BindingHandler(self.client)

        # Resolve group
        group = group_handler.get(group_id)
        if not group:
            group = group_handler.get_by_name(group_id)

        if not group:
            return {"error": f"Group not found: {group_id}"}

        group_uuid = group.get("uuid", group_id)
        group_name = group.get("name", group_id)

        # Get bindings for this group
        bindings = binding_handler.get_for_group(group_uuid)

        policy_permissions = []
        for binding in bindings:
            policy_uuid = binding.get("policyUuid", "")
            policy = policy_handler.get(policy_uuid)

            if policy:
                statement = policy.get("statementQuery", "")
                permissions = parse_statement_query(statement)

                for perm in permissions:
                    policy_permissions.append({
                        "policy_uuid": policy_uuid,
                        "policy_name": policy.get("name", ""),
                        "boundary": binding.get("boundaryUuid"),
                        **perm,
                    })

        # Aggregate unique permissions
        unique_permissions = {}
        for perm in policy_permissions:
            key = f"{perm['effect']}:{perm['action']}"
            if key not in unique_permissions:
                unique_permissions[key] = {
                    "effect": perm["effect"],
                    "action": perm["action"],
                    "description": perm["description"],
                    "sources": [],
                }
            unique_permissions[key]["sources"].append({
                "policy": perm["policy_name"],
                "boundary": perm.get("boundary"),
            })

        return {
            "group": {
                "uuid": group_uuid,
                "name": group_name,
            },
            "bindings": bindings,
            "binding_count": len(bindings),
            "effective_permissions": list(unique_permissions.values()),
            "permission_count": len(unique_permissions),
        }


class PermissionsMatrix:
    """Generates permissions matrix for policies and groups."""

    def __init__(self, client: Client):
        self.client = client

    def generate_policy_matrix(self) -> dict[str, Any]:
        """Generate a matrix of policies and their permissions.

        Returns:
            Dictionary with matrix data
        """
        from dtiam.resources.policies import PolicyHandler

        policy_handler = PolicyHandler(
            self.client, level_type="account", level_id=self.client.account_uuid
        )

        policies = policy_handler.list()

        # Collect all unique permissions
        all_permissions = set()
        policy_permissions = {}

        for policy in policies:
            policy_name = policy.get("name", "")
            policy_uuid = policy.get("uuid", "")

            # Get full policy details
            policy_detail = policy_handler.get(policy_uuid)
            statement = policy_detail.get("statementQuery", "") if policy_detail else ""

            permissions = parse_statement_query(statement)
            perm_set = set()

            for perm in permissions:
                perm_key = f"{perm['effect']}:{perm['action']}"
                all_permissions.add(perm_key)
                perm_set.add(perm_key)

            policy_permissions[policy_name] = {
                "uuid": policy_uuid,
                "permissions": perm_set,
            }

        # Build matrix
        permission_list = sorted(all_permissions)
        matrix = []

        for policy_name, data in policy_permissions.items():
            row = {
                "policy_name": policy_name,
                "policy_uuid": data["uuid"],
            }
            for perm in permission_list:
                row[perm] = perm in data["permissions"]
            matrix.append(row)

        return {
            "permissions": permission_list,
            "policies": list(policy_permissions.keys()),
            "matrix": matrix,
            "policy_count": len(policies),
            "permission_count": len(permission_list),
        }

    def generate_group_matrix(self) -> dict[str, Any]:
        """Generate a matrix of groups and their effective permissions.

        Returns:
            Dictionary with matrix data
        """
        from dtiam.resources.groups import GroupHandler
        from dtiam.resources.bindings import BindingHandler
        from dtiam.resources.policies import PolicyHandler

        group_handler = GroupHandler(self.client)
        binding_handler = BindingHandler(self.client)
        policy_handler = PolicyHandler(
            self.client, level_type="account", level_id=self.client.account_uuid
        )

        groups = group_handler.list()

        # Collect all unique permissions
        all_permissions = set()
        group_permissions = {}

        for group in groups:
            group_name = group.get("name", "")
            group_uuid = group.get("uuid", "")

            bindings = binding_handler.get_for_group(group_uuid)
            perm_set = set()

            for binding in bindings:
                policy_uuid = binding.get("policyUuid", "")
                policy = policy_handler.get(policy_uuid)

                if policy:
                    statement = policy.get("statementQuery", "")
                    permissions = parse_statement_query(statement)

                    for perm in permissions:
                        perm_key = f"{perm['effect']}:{perm['action']}"
                        all_permissions.add(perm_key)
                        perm_set.add(perm_key)

            group_permissions[group_name] = {
                "uuid": group_uuid,
                "permissions": perm_set,
            }

        # Build matrix
        permission_list = sorted(all_permissions)
        matrix = []

        for group_name, data in group_permissions.items():
            row = {
                "group_name": group_name,
                "group_uuid": data["uuid"],
            }
            for perm in permission_list:
                row[perm] = perm in data["permissions"]
            matrix.append(row)

        return {
            "permissions": permission_list,
            "groups": list(group_permissions.keys()),
            "matrix": matrix,
            "group_count": len(groups),
            "permission_count": len(permission_list),
        }


EntityType = Literal["user", "group"]


class EffectivePermissionsAPI:
    """Direct API client for effective permissions resolution.

    Uses the Dynatrace API endpoint:
    /iam/v1/resolution/{levelType}/{levelId}/effectivepermissions
    """

    def __init__(self, client: Client):
        self.client = client

    def get_effective_permissions(
        self,
        entity_id: str,
        entity_type: EntityType,
        level_type: str = "account",
        level_id: str | None = None,
        services: list[str] | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """Get effective permissions from the Dynatrace API.

        This calls the resolution API to get permissions as computed by Dynatrace,
        which may differ from local calculation.

        Args:
            entity_id: User UID or Group UUID
            entity_type: "user" or "group"
            level_type: Level type (account, environment, global)
            level_id: Level ID (uses account UUID if not specified)
            services: Filter by services
            page: Page number (default: 1)
            page_size: Page size (default: 100)

        Returns:
            Dictionary with effective permissions from API
        """
        if level_id is None:
            level_id = self.client.account_uuid

        # Build the resolution API path
        # Note: This is relative to the base API, not the account path
        base_url = "https://api.dynatrace.com/iam/v1"
        path = f"{base_url}/resolution/{level_type}/{level_id}/effectivepermissions"

        params: dict[str, Any] = {
            "entityId": entity_id,
            "entityType": entity_type,
            "page": page,
            "size": page_size,
        }

        if services:
            params["services"] = ",".join(services)

        try:
            response = self.client.request("GET", path, params=params)
            return response.json()
        except APIError as e:
            return {
                "error": str(e),
                "status_code": e.status_code,
            }

    def get_user_effective_permissions(
        self,
        user_id: str,
        level_type: str = "account",
        level_id: str | None = None,
        services: list[str] | None = None,
        all_pages: bool = True,
    ) -> dict[str, Any]:
        """Get effective permissions for a user via the API.

        Args:
            user_id: User UID or email
            level_type: Level type (account, environment, global)
            level_id: Level ID (uses account UUID if not specified)
            services: Filter by services
            all_pages: Fetch all pages of results

        Returns:
            Dictionary with effective permissions
        """
        from dtiam.resources.users import UserHandler

        # Resolve user email to UID if needed
        if "@" in user_id:
            user_handler = UserHandler(self.client)
            user = user_handler.get_by_email(user_id)
            if not user:
                return {"error": f"User not found: {user_id}"}
            user_id = user.get("uid", user_id)

        if not all_pages:
            return self.get_effective_permissions(
                entity_id=user_id,
                entity_type="user",
                level_type=level_type,
                level_id=level_id,
                services=services,
            )

        # Fetch all pages
        all_permissions: list[dict[str, Any]] = []
        page = 1
        page_size = 100

        while True:
            result = self.get_effective_permissions(
                entity_id=user_id,
                entity_type="user",
                level_type=level_type,
                level_id=level_id,
                services=services,
                page=page,
                page_size=page_size,
            )

            if "error" in result:
                return result

            permissions = result.get("effectivePermissions", result.get("items", []))
            all_permissions.extend(permissions)

            # Check if there are more pages
            total = result.get("total", len(permissions))
            if len(all_permissions) >= total or not permissions:
                break

            page += 1

        return {
            "entityId": user_id,
            "entityType": "user",
            "levelType": level_type,
            "levelId": level_id or self.client.account_uuid,
            "effectivePermissions": all_permissions,
            "total": len(all_permissions),
        }

    def get_group_effective_permissions(
        self,
        group_id: str,
        level_type: str = "account",
        level_id: str | None = None,
        services: list[str] | None = None,
        all_pages: bool = True,
    ) -> dict[str, Any]:
        """Get effective permissions for a group via the API.

        Args:
            group_id: Group UUID or name
            level_type: Level type (account, environment, global)
            level_id: Level ID (uses account UUID if not specified)
            services: Filter by services
            all_pages: Fetch all pages of results

        Returns:
            Dictionary with effective permissions
        """
        from dtiam.resources.groups import GroupHandler

        # Resolve group name to UUID if needed
        group_handler = GroupHandler(self.client)
        group = group_handler.get(group_id)
        if not group:
            group = group_handler.get_by_name(group_id)
        if not group:
            return {"error": f"Group not found: {group_id}"}

        group_uuid = group.get("uuid", group_id)

        if not all_pages:
            return self.get_effective_permissions(
                entity_id=group_uuid,
                entity_type="group",
                level_type=level_type,
                level_id=level_id,
                services=services,
            )

        # Fetch all pages
        all_permissions: list[dict[str, Any]] = []
        page = 1
        page_size = 100

        while True:
            result = self.get_effective_permissions(
                entity_id=group_uuid,
                entity_type="group",
                level_type=level_type,
                level_id=level_id,
                services=services,
                page=page,
                page_size=page_size,
            )

            if "error" in result:
                return result

            permissions = result.get("effectivePermissions", result.get("items", []))
            all_permissions.extend(permissions)

            # Check if there are more pages
            total = result.get("total", len(permissions))
            if len(all_permissions) >= total or not permissions:
                break

            page += 1

        return {
            "entityId": group_uuid,
            "entityType": "group",
            "levelType": level_type,
            "levelId": level_id or self.client.account_uuid,
            "effectivePermissions": all_permissions,
            "total": len(all_permissions),
        }
