"""Platform token resource handler for Dynatrace IAM API.

Handles platform token operations including list, create (generate), and delete.
Platform tokens are used for API access and require the `platform-token:tokens:manage` scope.
"""

from __future__ import annotations

from typing import Any

from dtiam.client import APIError
from dtiam.resources.base import ResourceHandler


class PlatformTokenHandler(ResourceHandler[Any]):
    """Handler for IAM platform token resources.

    Platform tokens provide API access credentials that can be used for
    automation and programmatic access to Dynatrace APIs.
    """

    @property
    def resource_name(self) -> str:
        return "platform-token"

    @property
    def api_path(self) -> str:
        return "/platform-tokens"

    @property
    def id_field(self) -> str:
        return "id"

    def list(self, **params: Any) -> list[dict[str, Any]]:
        """List all platform tokens in the account.

        Args:
            **params: Query parameters for filtering

        Returns:
            List of platform token dictionaries
        """
        try:
            response = self.client.get(self.api_path, params=params)
            data = response.json()

            if isinstance(data, dict):
                return data.get("items", data.get("platformTokens", data.get("tokens", [])))
            return data if isinstance(data, list) else []

        except APIError as e:
            self._handle_error("list", e)
            return []

    def get(self, token_id: str) -> dict[str, Any]:
        """Get a platform token by ID.

        Args:
            token_id: Platform token ID

        Returns:
            Platform token dictionary
        """
        try:
            response = self.client.get(f"{self.api_path}/{token_id}")
            return response.json()
        except APIError as e:
            self._handle_error("get", e)
            return {}

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get a platform token by name.

        Args:
            name: Platform token name

        Returns:
            Platform token dictionary or None if not found
        """
        tokens = self.list()
        for token in tokens:
            if token.get("name", "").lower() == name.lower():
                return token
        return None

    def create(
        self,
        name: str,
        scopes: list[str] | None = None,
        expires_in: str | None = None,
    ) -> dict[str, Any]:
        """Generate a new platform token.

        Args:
            name: Token name/description (required)
            scopes: List of scopes for the token (optional)
            expires_in: Token expiration time (optional, e.g., "30d", "1y")

        Returns:
            Created platform token dictionary (includes the actual token value)

        Note:
            The token value is only returned once during creation.
            It cannot be retrieved later, so save it immediately.
        """
        data: dict[str, Any] = {"name": name}

        if scopes:
            data["scopes"] = scopes
        if expires_in:
            data["expiresIn"] = expires_in

        try:
            response = self.client.post(self.api_path, json=data)
            return response.json()
        except APIError as e:
            self._handle_error("create", e)
            return {}

    def delete(self, token_id: str) -> bool:
        """Delete a platform token.

        Args:
            token_id: Platform token ID

        Returns:
            True if deleted successfully
        """
        try:
            self.client.delete(f"{self.api_path}/{token_id}")
            return True
        except APIError as e:
            self._handle_error("delete", e)
            return False

    def exists(self, token_id: str) -> bool:
        """Check if a platform token exists.

        Args:
            token_id: Platform token ID

        Returns:
            True if token exists
        """
        try:
            self.client.get(f"{self.api_path}/{token_id}")
            return True
        except APIError:
            return False
