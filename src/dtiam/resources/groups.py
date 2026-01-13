"""Group resource handler for Dynatrace IAM API.

Handles group CRUD operations and related queries like members and policies.
"""

from __future__ import annotations

from typing import Any

from dtiam.client import Client, APIError
from dtiam.resources.base import CRUDHandler


class GroupHandler(CRUDHandler[Any]):
    """Handler for IAM group resources."""

    @property
    def resource_name(self) -> str:
        return "group"

    @property
    def api_path(self) -> str:
        return "/groups"

    @property
    def list_key(self) -> str:
        return "items"

    @property
    def id_field(self) -> str:
        return "uuid"

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new group.

        The IAM API expects group creation data as an array of objects.

        Args:
            data: Group data with required fields:
                - name: Group name
                - description: Optional description

        Returns:
            Created group dictionary

        Raises:
            ValueError: If name is not provided
        """
        # Ensure required fields
        if "name" not in data:
            raise ValueError("Group name is required")

        try:
            # API expects array of groups
            payload = [data]
            response = self.client.post(self.api_path, json=payload)
            result = response.json()

            # API returns array of created groups
            if isinstance(result, list) and result:
                return result[0]
            elif isinstance(result, dict):
                items = result.get("items", [result])
                return items[0] if items else {}
            return {}
        except APIError as e:
            self._handle_error("create", e)
            return {}

    def get_members(self, group_id: str) -> list[dict[str, Any]]:
        """Get members of a group.

        Args:
            group_id: Group UUID

        Returns:
            List of user dictionaries
        """
        try:
            response = self.client.get(f"{self.api_path}/{group_id}/users")
            data = response.json()
            if isinstance(data, dict):
                return data.get("items", data.get("users", []))
            return data if isinstance(data, list) else []
        except APIError as e:
            self._handle_error("get members", e)
            return []

    def get_member_count(self, group_id: str) -> int:
        """Get the count of members in a group.

        Args:
            group_id: Group UUID

        Returns:
            Number of members
        """
        try:
            response = self.client.get(f"{self.api_path}/{group_id}/users", params={"count": "true"})
            data = response.json()
            if isinstance(data, dict):
                return data.get("count", data.get("totalCount", len(data.get("items", []))))
            return len(data) if isinstance(data, list) else 0
        except APIError:
            return 0

    def add_member(self, group_id: str, user_email: str) -> bool:
        """Add a user to a group.

        Args:
            group_id: Group UUID
            user_email: User email address

        Returns:
            True if successful
        """
        try:
            self.client.post(f"{self.api_path}/{group_id}/users", json={"email": user_email})
            return True
        except APIError as e:
            self._handle_error("add member", e)
            return False

    def remove_member(self, group_id: str, user_id: str) -> bool:
        """Remove a user from a group.

        Args:
            group_id: Group UUID
            user_id: User UID

        Returns:
            True if successful
        """
        try:
            self.client.delete(f"{self.api_path}/{group_id}/users/{user_id}")
            return True
        except APIError as e:
            self._handle_error("remove member", e)
            return False

    def get_policies(self, group_id: str) -> list[str]:
        """Get policy UUIDs bound to a group.

        This retrieves the policy bindings for the group.

        Args:
            group_id: Group UUID

        Returns:
            List of policy UUIDs
        """
        try:
            # Get bindings for the group - must use full URL since /repo/ is not under /accounts/
            response = self.client.get(
                f"https://api.dynatrace.com/iam/v1/repo/account/{self.client.account_uuid}/bindings/groups/{group_id}"
            )
            data = response.json()

            # Extract policy UUIDs from bindings
            policy_uuids = []
            bindings = data.get("policyBindings", [])
            for binding in bindings:
                policy_uuid = binding.get("policyUuid")
                if policy_uuid and policy_uuid not in policy_uuids:
                    policy_uuids.append(policy_uuid)

            return policy_uuids
        except APIError:
            return []

    def get_expanded(self, group_id: str) -> dict[str, Any]:
        """Get group with expanded details including members and policies.

        Args:
            group_id: Group UUID

        Returns:
            Group dictionary with expanded information
        """
        group = self.get(group_id)
        if not group:
            return {}

        # Add member information
        group["members"] = self.get_members(group_id)
        group["member_count"] = len(group["members"])

        # Add policy information
        group["policy_uuids"] = self.get_policies(group_id)
        group["policy_count"] = len(group["policy_uuids"])

        return group


    def clone(
        self,
        source_group_id: str,
        new_name: str,
        new_description: str | None = None,
        include_members: bool = False,
        include_policies: bool = True,
    ) -> dict[str, Any]:
        """Clone an existing group.

        Args:
            source_group_id: UUID of group to clone
            new_name: Name for the new group
            new_description: Description for new group (uses source if None)
            include_members: Copy members to new group
            include_policies: Copy policy bindings to new group

        Returns:
            Created group dictionary
        """
        from dtiam.resources.bindings import BindingHandler

        # Get source group
        source = self.get(source_group_id)
        if not source:
            raise ValueError(f"Source group not found: {source_group_id}")

        # Create new group
        new_group = self.create({
            "name": new_name,
            "description": new_description or source.get("description", ""),
        })

        new_group_id = new_group.get("uuid", "")

        # Copy members if requested
        if include_members:
            members = self.get_members(source_group_id)
            for member in members:
                email = member.get("email", "")
                if email:
                    self.add_member(new_group_id, email)

        # Copy policies if requested
        if include_policies:
            binding_handler = BindingHandler(self.client)
            bindings = binding_handler.get_for_group(source_group_id)
            for binding in bindings:
                policy_uuid = binding.get("policyUuid", "")
                boundary_uuid = binding.get("boundaryUuid")
                boundaries = [boundary_uuid] if boundary_uuid else []
                binding_handler.create(
                    group_uuid=new_group_id,
                    policy_uuid=policy_uuid,
                    boundaries=boundaries,
                )

        return new_group

    def setup_with_policy(
        self,
        group_name: str,
        policy_uuid: str,
        boundary_uuid: str | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a group and bind a policy in one operation.

        Args:
            group_name: Name for the new group
            policy_uuid: Policy to bind to the group
            boundary_uuid: Optional boundary to apply
            description: Group description

        Returns:
            Dictionary with created group and binding info
        """
        from dtiam.resources.bindings import BindingHandler

        # Create group
        group = self.create({
            "name": group_name,
            "description": description,
        })

        group_uuid = group.get("uuid", "")

        # Create binding
        binding_handler = BindingHandler(self.client)
        boundaries = [boundary_uuid] if boundary_uuid else []
        binding = binding_handler.create(
            group_uuid=group_uuid,
            policy_uuid=policy_uuid,
            boundaries=boundaries,
        )

        return {
            "group": group,
            "binding": binding,
        }
