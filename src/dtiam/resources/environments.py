"""Environment resource handler for Dynatrace Account API.

Handles listing and retrieving Dynatrace environments/tenants within an account.
"""

from __future__ import annotations

from typing import Any

from dtiam.client import APIError
from dtiam.resources.base import ResourceHandler


class EnvironmentHandler(ResourceHandler[Any]):
    """Handler for Dynatrace environment resources.

    Environments (tenants) are managed at the account level.
    This uses the Account Management API v2 endpoints.
    """

    @property
    def resource_name(self) -> str:
        return "environment"

    @property
    def api_path(self) -> str:
        # Environments use a different API base
        # https://api.dynatrace.com/env/v2/accounts/{accountUuid}/environments
        return f"https://api.dynatrace.com/env/v2/accounts/{self.client.account_uuid}/environments"

    @property
    def id_field(self) -> str:
        return "id"

    def list(self, **params: Any) -> list[dict[str, Any]]:
        """List all environments in the account.

        Args:
            **params: Query parameters for filtering

        Returns:
            List of environment dictionaries
        """
        try:
            response = self.client.get(self.api_path, params=params)
            data = response.json()

            if isinstance(data, dict):
                return data.get("tenants", data.get("environments", data.get("items", [])))
            return data if isinstance(data, list) else []

        except APIError as e:
            self._handle_error("list", e)
            return []

    def get(self, environment_id: str) -> dict[str, Any]:
        """Get a single environment by ID.

        Args:
            environment_id: Environment ID

        Returns:
            Environment dictionary
        """
        try:
            response = self.client.get(f"{self.api_path}/{environment_id}")
            return response.json()
        except APIError as e:
            self._handle_error("get", e)
            return {}

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get an environment by name.

        Args:
            name: Environment name

        Returns:
            Environment dictionary or None if not found
        """
        environments = self.list()
        for env in environments:
            if env.get("name") == name:
                return env
        return None
