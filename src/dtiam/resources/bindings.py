"""Policy binding resource handler for Dynatrace IAM API.

Handles policy binding operations - connecting groups to policies.
"""

from __future__ import annotations

from typing import Any, Literal

from dtiam.client import APIError
from dtiam.resources.base import ResourceHandler


LevelType = Literal["account", "environment"]


class BindingHandler(ResourceHandler[Any]):
    """Handler for IAM policy binding resources.

    Policy bindings connect groups to policies at different levels.
    """

    def __init__(
        self,
        client: Any,
        level_type: LevelType = "account",
        level_id: str | None = None,
    ):
        """Initialize binding handler.

        Args:
            client: API client
            level_type: Binding level (account or environment)
            level_id: Level identifier (account UUID or environment ID)
        """
        super().__init__(client)
        self.level_type = level_type
        self.level_id = level_id or client.account_uuid

    @property
    def resource_name(self) -> str:
        return "binding"

    @property
    def api_path(self) -> str:
        # Bindings use repo path which is NOT under /accounts/{uuid}/
        # Must return full URL since /repo/ is at /iam/v1/repo/, not /iam/v1/accounts/{uuid}/repo/
        return f"https://api.dynatrace.com/iam/v1/repo/{self.level_type}/{self.level_id}/bindings"

    def list(self, **params: Any) -> list[dict[str, Any]]:
        """List all bindings at the configured level.

        Args:
            **params: Query parameters for filtering

        Returns:
            List of binding dictionaries
        """
        try:
            response = self.client.get(self.api_path, params=params)
            data = response.json()

            if isinstance(data, dict):
                # Bindings may be nested under policyBindings
                bindings = data.get("policyBindings", data.get("bindings", []))
                # Flatten the bindings structure for easier consumption
                flat_bindings = []
                for binding in bindings:
                    policy_uuid = binding.get("policyUuid")
                    groups = binding.get("groups", [])
                    boundaries = binding.get("boundaries", [])
                    for group_uuid in groups:
                        flat_bindings.append({
                            "policyUuid": policy_uuid,
                            "groupUuid": group_uuid,
                            "boundaries": boundaries,
                            "levelType": self.level_type,
                            "levelId": self.level_id,
                        })
                return flat_bindings
            return []

        except APIError as e:
            self._handle_error("list", e)
            return []

    def list_raw(self, **params: Any) -> dict[str, Any]:
        """List bindings in raw API format.

        Args:
            **params: Query parameters for filtering

        Returns:
            Raw API response dictionary
        """
        try:
            response = self.client.get(self.api_path, params=params)
            return response.json()
        except APIError as e:
            self._handle_error("list", e)
            return {}

    def get_for_group(self, group_id: str) -> list[dict[str, Any]]:
        """Get all bindings for a specific group.

        Args:
            group_id: Group UUID

        Returns:
            List of binding dictionaries for the group
        """
        try:
            response = self.client.get(f"{self.api_path}/groups/{group_id}")
            data = response.json()

            if isinstance(data, dict):
                bindings = data.get("policyBindings", [])
                flat_bindings = []
                for binding in bindings:
                    flat_bindings.append({
                        "policyUuid": binding.get("policyUuid"),
                        "groupUuid": group_id,
                        "boundaries": binding.get("boundaries", []),
                        "levelType": self.level_type,
                        "levelId": self.level_id,
                    })
                return flat_bindings
            return []

        except APIError as e:
            self._handle_error("get bindings for group", e)
            return []

    def create(
        self,
        group_uuid: str,
        policy_uuid: str,
        boundaries: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new policy binding.

        Uses: POST /iam/v1/repo/{levelType}/{levelId}/bindings/{policyUuid}

        Args:
            group_uuid: Group UUID to bind
            policy_uuid: Policy UUID to bind to the group
            boundaries: Optional list of boundary UUIDs

        Returns:
            Created/updated binding dictionary
        """
        # Payload contains groups and boundaries arrays
        data = {
            "groups": [group_uuid],
            "boundaries": boundaries or [],
        }

        try:
            # POST /iam/v1/repo/{levelType}/{levelId}/bindings/{policyUuid}
            response = self.client.post(f"{self.api_path}/{policy_uuid}", json=data)
            # Handle empty response (204 No Content or empty body)
            try:
                return response.json() if response.text else {}
            except Exception:
                return {}
        except APIError as e:
            self._handle_error("create", e)
            return {}

    def create_or_update(
        self,
        group_uuid: str,
        policy_uuid: str,
        boundaries: list[str] | None = None,
    ) -> tuple[dict[str, Any], str]:
        """Create a binding or update if it exists.

        First tries to create the binding. If it already exists, updates
        the binding with the specified boundaries.

        Args:
            group_uuid: Group UUID to bind
            policy_uuid: Policy UUID to bind to the group
            boundaries: Optional list of boundary UUIDs

        Returns:
            Tuple of (binding dictionary, action) where action is "created", "updated", or "unchanged"
        """
        # First try to create
        data = {
            "groups": [group_uuid],
            "boundaries": boundaries or [],
        }

        try:
            # POST /iam/v1/repo/{levelType}/{levelId}/bindings/{policyUuid}
            response = self.client.post(f"{self.api_path}/{policy_uuid}", json=data)
            # Handle empty response (204 No Content or empty body)
            try:
                result = response.json() if response.text else {}
            except Exception:
                result = {}
            return result, "created"
        except APIError as e:
            # Check if binding already exists (400 error)
            if e.status_code == 400 and e.response_body and "already exists" in e.response_body.lower():
                # Update existing binding with boundaries
                if boundaries:
                    try:
                        # POST /iam/v1/repo/{levelType}/{levelId}/bindings/{policyUuid}/{groupUuid}
                        response = self.client.post(
                            f"{self.api_path}/{policy_uuid}/{group_uuid}",
                            json={"boundaries": boundaries}
                        )
                        # Handle empty response
                        try:
                            result = response.json() if response.text else {}
                        except Exception:
                            result = {}
                        return result, "updated"
                    except APIError:
                        pass
                return {}, "unchanged"
            self._handle_error("create", e)
            return {}, "error"

    def delete(
        self,
        group_uuid: str,
        policy_uuid: str,
    ) -> bool:
        """Delete a policy binding.

        Args:
            group_uuid: Group UUID
            policy_uuid: Policy UUID

        Returns:
            True if deleted successfully
        """
        # Deletion typically requires updating the bindings to remove the group
        try:
            # Get current bindings
            current = self.list_raw()
            bindings = current.get("policyBindings", [])

            # Find and update the relevant binding
            updated = False
            for binding in bindings:
                if binding.get("policyUuid") == policy_uuid:
                    groups = binding.get("groups", [])
                    if group_uuid in groups:
                        groups.remove(group_uuid)
                        updated = True
                        break

            if updated:
                # PUT the updated bindings
                self.client.put(self.api_path, json={"policyBindings": bindings})
                return True
            return False

        except APIError as e:
            self._handle_error("delete", e)
            return False

    def add_boundary(
        self,
        group_uuid: str,
        policy_uuid: str,
        boundary_uuid: str,
    ) -> bool:
        """Add a boundary to an existing binding.

        Args:
            group_uuid: Group UUID
            policy_uuid: Policy UUID
            boundary_uuid: Boundary UUID to add

        Returns:
            True if successful
        """
        try:
            current = self.list_raw()
            bindings = current.get("policyBindings", [])

            for binding in bindings:
                if binding.get("policyUuid") == policy_uuid:
                    groups = binding.get("groups", [])
                    if group_uuid in groups:
                        boundaries = binding.get("boundaries", [])
                        if boundary_uuid not in boundaries:
                            boundaries.append(boundary_uuid)
                            binding["boundaries"] = boundaries
                            self.client.put(self.api_path, json={"policyBindings": bindings})
                            return True
            return False

        except APIError as e:
            self._handle_error("add boundary", e)
            return False

    def remove_boundary(
        self,
        group_uuid: str,
        policy_uuid: str,
        boundary_uuid: str,
    ) -> bool:
        """Remove a boundary from an existing binding.

        Args:
            group_uuid: Group UUID
            policy_uuid: Policy UUID
            boundary_uuid: Boundary UUID to remove

        Returns:
            True if successful
        """
        try:
            current = self.list_raw()
            bindings = current.get("policyBindings", [])

            for binding in bindings:
                if binding.get("policyUuid") == policy_uuid:
                    groups = binding.get("groups", [])
                    if group_uuid in groups:
                        boundaries = binding.get("boundaries", [])
                        if boundary_uuid in boundaries:
                            boundaries.remove(boundary_uuid)
                            binding["boundaries"] = boundaries
                            self.client.put(self.api_path, json={"policyBindings": bindings})
                            return True
            return False

        except APIError as e:
            self._handle_error("remove boundary", e)
            return False

    def get_for_policy(self, policy_uuid: str) -> list[dict[str, Any]]:
        """Get all bindings for a specific policy.

        Args:
            policy_uuid: Policy UUID

        Returns:
            List of binding dictionaries for the policy
        """
        try:
            response = self.client.get(f"{self.api_path}/{policy_uuid}")
            data = response.json()

            if isinstance(data, dict):
                groups = data.get("groups", [])
                boundaries = data.get("boundaries", [])
                return [{
                    "policyUuid": policy_uuid,
                    "groups": groups,
                    "boundaries": boundaries,
                    "levelType": self.level_type,
                    "levelId": self.level_id,
                }]
            return []

        except APIError as e:
            self._handle_error("get bindings for policy", e)
            return []

    def get_policy_group_binding(
        self,
        policy_uuid: str,
        group_uuid: str,
    ) -> dict[str, Any]:
        """Get binding for a specific policy-group combination.

        Args:
            policy_uuid: Policy UUID
            group_uuid: Group UUID

        Returns:
            Binding dictionary for the specific policy-group combination
        """
        try:
            response = self.client.get(
                f"{self.api_path}/{policy_uuid}/{group_uuid}"
            )
            data = response.json()

            return {
                "policyUuid": policy_uuid,
                "groupUuid": group_uuid,
                "boundaries": data.get("boundaries", []),
                "levelType": self.level_type,
                "levelId": self.level_id,
            }

        except APIError as e:
            self._handle_error("get policy-group binding", e)
            return {}

    def get_descendants(self, policy_uuid: str) -> list[dict[str, Any]]:
        """Get bindings in descendant levels for a policy.

        This returns bindings from child levels (e.g., environment bindings
        when queried at account level).

        Args:
            policy_uuid: Policy UUID

        Returns:
            List of binding dictionaries from descendant levels
        """
        try:
            response = self.client.get(
                f"{self.api_path}/descendants/{policy_uuid}"
            )
            data = response.json()

            if isinstance(data, dict):
                bindings = data.get("policyBindings", data.get("bindings", []))
                flat_bindings = []
                for binding in bindings:
                    groups = binding.get("groups", [])
                    boundaries = binding.get("boundaries", [])
                    level_type = binding.get("levelType", self.level_type)
                    level_id = binding.get("levelId", self.level_id)
                    for group_uuid in groups:
                        flat_bindings.append({
                            "policyUuid": policy_uuid,
                            "groupUuid": group_uuid,
                            "boundaries": boundaries,
                            "levelType": level_type,
                            "levelId": level_id,
                        })
                return flat_bindings
            return []

        except APIError as e:
            self._handle_error("get descendant bindings", e)
            return []

    def update_group_bindings(
        self,
        group_uuid: str,
        policy_bindings: list[dict[str, Any]],
    ) -> bool:
        """Update all policy bindings for a group.

        This replaces all policy bindings for the specified group.

        Args:
            group_uuid: Group UUID
            policy_bindings: List of policy binding dictionaries with:
                - policyUuid: Policy UUID
                - boundaries: Optional list of boundary UUIDs

        Returns:
            True if successful
        """
        try:
            self.client.put(
                f"{self.api_path}/groups/{group_uuid}",
                json={"policyBindings": policy_bindings},
            )
            return True
        except APIError as e:
            self._handle_error("update group bindings", e)
            return False
