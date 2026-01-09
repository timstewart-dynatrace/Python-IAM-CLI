"""User resource handler for Dynatrace IAM API.

Handles user operations including creation and management.
"""

from __future__ import annotations

from typing import Any

from dtiam.client import APIError
from dtiam.resources.base import ResourceHandler


class UserHandler(ResourceHandler[Any]):
    """Handler for IAM user resources.

    Supports user creation, listing, and group membership operations.
    """

    @property
    def resource_name(self) -> str:
        return "user"

    @property
    def api_path(self) -> str:
        return "/users"

    @property
    def id_field(self) -> str:
        return "uid"

    def list(
        self,
        include_service_users: bool = False,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """List all users in the account.

        Args:
            include_service_users: Include service users in results
            **params: Query parameters for filtering

        Returns:
            List of user dictionaries
        """
        try:
            if include_service_users:
                params["service-users"] = "true"

            response = self.client.get(self.api_path, params=params)
            data = response.json()

            if isinstance(data, dict):
                return data.get("items", data.get("users", []))
            return data if isinstance(data, list) else []

        except APIError as e:
            self._handle_error("list", e)
            return []

    def create(
        self,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
        groups: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new user in the account.

        Args:
            email: User email address (required)
            first_name: User's first name
            last_name: User's last name
            groups: List of group UUIDs to add user to

        Returns:
            Created user dictionary
        """
        data: dict[str, Any] = {"email": email}

        if first_name:
            data["name"] = first_name
        if last_name:
            data["surname"] = last_name
        if groups:
            data["groups"] = groups

        try:
            response = self.client.post(self.api_path, json=data)
            return response.json()
        except APIError as e:
            self._handle_error("create", e)
            return {}

    def delete(self, user_id: str) -> bool:
        """Delete a user from the account.

        Args:
            user_id: User UID

        Returns:
            True if deleted successfully
        """
        try:
            self.client.delete(f"{self.api_path}/{user_id}")
            return True
        except APIError as e:
            self._handle_error("delete", e)
            return False

    def get(self, user_id: str) -> dict[str, Any]:
        """Get a single user by UID.

        Args:
            user_id: User UID

        Returns:
            User dictionary
        """
        try:
            response = self.client.get(f"{self.api_path}/{user_id}")
            return response.json()
        except APIError as e:
            self._handle_error("get", e)
            return {}

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        """Get a user by email address.

        Args:
            email: User email address

        Returns:
            User dictionary or None if not found
        """
        users = self.list()
        for user in users:
            if user.get("email", "").lower() == email.lower():
                return user
        return None

    def get_groups(self, user_id: str) -> list[dict[str, Any]]:
        """Get the groups a user belongs to.

        Args:
            user_id: User UID

        Returns:
            List of group dictionaries
        """
        try:
            response = self.client.get(f"{self.api_path}/{user_id}/groups")
            data = response.json()

            if isinstance(data, dict):
                return data.get("items", data.get("groups", []))
            return data if isinstance(data, list) else []

        except APIError as e:
            # If the endpoint doesn't exist, try to get groups from user details
            user = self.get(user_id)
            if user:
                return user.get("groups", [])
            return []

    def get_expanded(self, user_id: str) -> dict[str, Any]:
        """Get user with expanded details including groups.

        Args:
            user_id: User UID

        Returns:
            User dictionary with expanded information
        """
        user = self.get(user_id)
        if not user:
            return {}

        # Add group information if not already present
        if "groups" not in user or not user["groups"]:
            user["groups"] = self.get_groups(user_id)

        user["group_count"] = len(user.get("groups", []))
        return user
