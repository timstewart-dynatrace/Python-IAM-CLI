"""Service user resource handler for Dynatrace IAM API.

Handles service user (OAuth client) operations including CRUD and group management.
"""

from __future__ import annotations

from typing import Any

from dtiam.client import APIError
from dtiam.resources.base import ResourceHandler


class ServiceUserHandler(ResourceHandler[Any]):
    """Handler for IAM service user resources.

    Service users are used for programmatic API access (OAuth clients).
    They can be assigned to groups just like regular users.
    """

    @property
    def resource_name(self) -> str:
        return "service-user"

    @property
    def api_path(self) -> str:
        return "/service-users"

    @property
    def id_field(self) -> str:
        return "uid"

    def list(self, **params: Any) -> list[dict[str, Any]]:
        """List all service users in the account.

        Args:
            **params: Query parameters for filtering

        Returns:
            List of service user dictionaries
        """
        try:
            response = self.client.get(self.api_path, params=params)
            data = response.json()

            if isinstance(data, dict):
                return data.get("items", data.get("serviceUsers", []))
            return data if isinstance(data, list) else []

        except APIError as e:
            self._handle_error("list", e)
            return []

    def get(self, user_id: str) -> dict[str, Any]:
        """Get a service user by UUID.

        Note: Falls back to filtering the list if the API doesn't support
        direct GET by UUID (similar to groups endpoint).

        Args:
            user_id: Service user UUID

        Returns:
            Service user dictionary or empty dict if not found
        """
        try:
            response = self.client.get(f"{self.api_path}/{user_id}")
            return response.json()
        except APIError as e:
            if e.status_code == 404:
                # Fall back to filtering the list
                users = self.list()
                for user in users:
                    if user.get("uid") == user_id:
                        return user
                return {}
            self._handle_error("get", e)
            return {}

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get a service user by name.

        Args:
            name: Service user name

        Returns:
            Service user dictionary or None if not found
        """
        users = self.list()
        for user in users:
            if user.get("name", "").lower() == name.lower():
                return user
        return None

    def create(
        self,
        name: str,
        description: str | None = None,
        groups: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new service user.

        Args:
            name: Service user name (required)
            description: Optional description
            groups: List of group UUIDs to add service user to

        Returns:
            Created service user dictionary (includes client credentials)
        """
        data: dict[str, Any] = {"name": name}

        if description:
            data["description"] = description
        if groups:
            data["groups"] = groups

        try:
            response = self.client.post(self.api_path, json=data)
            return response.json()
        except APIError as e:
            self._handle_error("create", e)
            return {}

    def update(
        self,
        user_id: str,
        name: str | None = None,
        description: str | None = None,
        groups: list[str] | None = None,
    ) -> dict[str, Any]:
        """Update a service user.

        Args:
            user_id: Service user UUID
            name: New name (optional)
            description: New description (optional)
            groups: New list of group UUIDs (optional, replaces existing)

        Returns:
            Updated service user dictionary
        """
        data: dict[str, Any] = {}

        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if groups is not None:
            data["groups"] = groups

        if not data:
            return self.get(user_id)

        try:
            response = self.client.put(f"{self.api_path}/{user_id}", json=data)
            return response.json()
        except APIError as e:
            self._handle_error("update", e)
            return {}

    def delete(self, user_id: str) -> bool:
        """Delete a service user.

        Args:
            user_id: Service user UUID

        Returns:
            True if deleted successfully
        """
        try:
            self.client.delete(f"{self.api_path}/{user_id}")
            return True
        except APIError as e:
            self._handle_error("delete", e)
            return False

    def get_groups(self, user_id: str) -> list[dict[str, Any]]:
        """Get the groups a service user belongs to.

        Args:
            user_id: Service user UUID

        Returns:
            List of group dictionaries
        """
        user = self.get(user_id)
        if user:
            groups = user.get("groups", [])
            # If groups are just UUIDs, fetch full group info
            if groups and isinstance(groups[0], str):
                from dtiam.resources.groups import GroupHandler
                group_handler = GroupHandler(self.client)
                full_groups = []
                for group_uuid in groups:
                    group = group_handler.get(group_uuid)
                    if group:
                        full_groups.append(group)
                return full_groups
            return groups
        return []

    def add_to_group(self, user_id: str, group_uuid: str) -> bool:
        """Add a service user to a group.

        Args:
            user_id: Service user UUID
            group_uuid: Group UUID to add to

        Returns:
            True if successful
        """
        user = self.get(user_id)
        if not user:
            return False

        current_groups = user.get("groups", [])
        # Handle both UUID strings and group objects
        group_uuids = [
            g if isinstance(g, str) else g.get("uuid", "")
            for g in current_groups
        ]

        if group_uuid not in group_uuids:
            group_uuids.append(group_uuid)
            result = self.update(user_id, groups=group_uuids)
            return bool(result)
        return True  # Already in group

    def remove_from_group(self, user_id: str, group_uuid: str) -> bool:
        """Remove a service user from a group.

        Args:
            user_id: Service user UUID
            group_uuid: Group UUID to remove from

        Returns:
            True if successful
        """
        user = self.get(user_id)
        if not user:
            return False

        current_groups = user.get("groups", [])
        # Handle both UUID strings and group objects
        group_uuids = [
            g if isinstance(g, str) else g.get("uuid", "")
            for g in current_groups
        ]

        if group_uuid in group_uuids:
            group_uuids.remove(group_uuid)
            result = self.update(user_id, groups=group_uuids)
            return bool(result)
        return True  # Already not in group

    def get_expanded(self, user_id: str) -> dict[str, Any]:
        """Get service user with expanded details including groups.

        Args:
            user_id: Service user UUID

        Returns:
            Service user dictionary with expanded information
        """
        user = self.get(user_id)
        if not user:
            return {}

        # Expand group information
        groups = user.get("groups", [])
        if groups and isinstance(groups[0], str):
            user["groups"] = self.get_groups(user_id)

        user["group_count"] = len(user.get("groups", []))
        return user
