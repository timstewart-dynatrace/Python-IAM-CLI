"""Policy resource handler for Dynatrace IAM API.

Handles IAM policy CRUD operations across different levels (account, environment, global).
"""

from __future__ import annotations

from typing import Any, Literal

from dtiam.client import Client, APIError
from dtiam.resources.base import ResourceHandler


LevelType = Literal["account", "environment", "global"]


class PolicyHandler(ResourceHandler[Any]):
    """Handler for IAM policy resources.

    Policies can exist at different levels:
    - account: Account-wide policies
    - environment: Environment-specific policies
    - global: Global built-in policies
    """

    def __init__(self, client: Client, level_type: LevelType = "account", level_id: str | None = None):
        """Initialize policy handler.

        Args:
            client: API client
            level_type: Policy level (account, environment, global)
            level_id: Level identifier (account UUID, environment ID, or "global")
        """
        super().__init__(client)
        self.level_type = level_type
        self.level_id = level_id or (
            client.account_uuid if level_type == "account" else "global"
        )

    @property
    def resource_name(self) -> str:
        return "policy"

    @property
    def api_path(self) -> str:
        # Policies use repo path which is NOT under /accounts/{uuid}/
        # Must return full URL since /repo/ is at /iam/v1/repo/, not /iam/v1/accounts/{uuid}/repo/
        return f"https://api.dynatrace.com/iam/v1/repo/{self.level_type}/{self.level_id}/policies"

    @property
    def id_field(self) -> str:
        return "uuid"

    def list(self, **params: Any) -> list[dict[str, Any]]:
        """List all policies at the configured level.

        Args:
            **params: Query parameters for filtering

        Returns:
            List of policy dictionaries
        """
        try:
            response = self.client.get(self.api_path, params=params)
            data = response.json()

            if isinstance(data, dict):
                return data.get("policies", data.get("items", []))
            return data if isinstance(data, list) else []

        except APIError as e:
            self._handle_error("list", e)
            return []

    def get(self, policy_id: str) -> dict[str, Any]:
        """Get a single policy by UUID.

        Args:
            policy_id: Policy UUID

        Returns:
            Policy dictionary
        """
        try:
            response = self.client.get(f"{self.api_path}/{policy_id}")
            return response.json()
        except APIError as e:
            self._handle_error("get", e)
            return {}

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new policy.

        Args:
            data: Policy data with required fields:
                - name: Policy name
                - statementQuery: Policy statement query

        Returns:
            Created policy dictionary
        """
        if "name" not in data:
            raise ValueError("Policy name is required")
        if "statementQuery" not in data:
            raise ValueError("Policy statementQuery is required")

        try:
            response = self.client.post(self.api_path, json=data)
            return response.json()
        except APIError as e:
            self._handle_error("create", e)
            return {}

    def update(self, policy_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing policy.

        Args:
            policy_id: Policy UUID
            data: Updated policy data

        Returns:
            Updated policy dictionary
        """
        try:
            response = self.client.put(f"{self.api_path}/{policy_id}", json=data)
            return response.json()
        except APIError as e:
            self._handle_error("update", e)
            return {}

    def delete(self, policy_id: str) -> bool:
        """Delete a policy.

        Args:
            policy_id: Policy UUID

        Returns:
            True if deleted successfully
        """
        try:
            self.client.delete(f"{self.api_path}/{policy_id}")
            return True
        except APIError as e:
            self._handle_error("delete", e)
            return False

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get a policy by name.

        Args:
            name: Policy name

        Returns:
            Policy dictionary or None if not found
        """
        policies = self.list()
        for policy in policies:
            if policy.get("name") == name:
                return policy
        return None

    def list_all_levels(self) -> list[dict[str, Any]]:
        """List policies from all levels (account, environments, global).

        Returns:
            Combined list of policies from all levels
        """
        all_policies = []

        # Account level
        account_handler = PolicyHandler(self.client, "account", self.client.account_uuid)
        account_policies = account_handler.list()
        for p in account_policies:
            p["_level_type"] = "account"
            p["_level_id"] = self.client.account_uuid
        all_policies.extend(account_policies)

        # Global level (built-in policies)
        try:
            global_handler = PolicyHandler(self.client, "global", "global")
            global_policies = global_handler.list()
            for p in global_policies:
                p["_level_type"] = "global"
                p["_level_id"] = "global"
            all_policies.extend(global_policies)
        except Exception:
            pass  # Global policies might not be accessible

        return all_policies

    def list_aggregate(self) -> list[dict[str, Any]]:
        """List all policies including inherited ones via the aggregate endpoint.

        This uses the /policies/aggregate endpoint which returns all policies
        at the current level plus inherited policies from parent levels.

        Returns:
            List of policy dictionaries including inherited policies
        """
        try:
            response = self.client.get(f"{self.api_path}/aggregate")
            data = response.json()

            if isinstance(data, dict):
                return data.get("policies", data.get("items", []))
            return data if isinstance(data, list) else []

        except APIError as e:
            self._handle_error("list aggregate", e)
            return []

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate a policy definition before creation.

        Args:
            data: Policy data to validate with required fields:
                - name: Policy name
                - statementQuery: Policy statement query

        Returns:
            Validation result dictionary with 'valid' boolean and 'errors' list
        """
        try:
            response = self.client.post(f"{self.api_path}/validation", json=data)
            return response.json()
        except APIError as e:
            # Return validation failure info
            return {
                "valid": False,
                "errors": [str(e)],
                "status_code": e.status_code,
            }

    def validate_update(self, policy_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Validate a policy update before applying.

        Args:
            policy_id: Policy UUID to update
            data: Updated policy data to validate

        Returns:
            Validation result dictionary with 'valid' boolean and 'errors' list
        """
        try:
            response = self.client.post(
                f"{self.api_path}/validation/{policy_id}",
                json=data,
            )
            return response.json()
        except APIError as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "status_code": e.status_code,
            }
