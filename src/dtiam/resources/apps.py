"""App Engine Registry resource handler.

Handles listing Dynatrace Apps from the App Engine Registry API.
These app IDs can be used in policy statements like:
    shared:app-id = '{app.id}';
"""

from __future__ import annotations

from typing import Any

from dtiam.client import APIError
from dtiam.resources.base import ResourceHandler


class AppHandler(ResourceHandler[Any]):
    """Handler for Dynatrace App Engine Registry resources.

    Apps are retrieved from environment-specific endpoints.
    Requires an environment URL (e.g., https://{env-id}.apps.dynatrace.com).
    """

    def __init__(self, client: Any, environment_url: str):
        """Initialize the app handler.

        Args:
            client: HTTP client for making requests
            environment_url: Base URL for the environment (e.g., https://abc12345.apps.dynatrace.com)
        """
        super().__init__(client)
        # Normalize the environment URL
        self.environment_url = environment_url.rstrip("/")
        if not self.environment_url.startswith("http"):
            self.environment_url = f"https://{self.environment_url}"

    @property
    def resource_name(self) -> str:
        return "app"

    @property
    def api_path(self) -> str:
        return f"{self.environment_url}/platform/app-engine/registry/v1/apps"

    @property
    def id_field(self) -> str:
        return "id"

    def list(self, **params: Any) -> list[dict[str, Any]]:
        """List all apps from the App Engine Registry.

        Args:
            **params: Query parameters for filtering

        Returns:
            List of app dictionaries
        """
        try:
            response = self.client.get(self.api_path, params=params)
            data = response.json()

            if isinstance(data, dict):
                return data.get("apps", data.get("items", []))
            return data if isinstance(data, list) else []

        except APIError as e:
            self._handle_error("list", e)
            return []

    def get(self, app_id: str) -> dict[str, Any]:
        """Get a single app by ID.

        Args:
            app_id: App ID

        Returns:
            App dictionary
        """
        try:
            response = self.client.get(f"{self.api_path}/{app_id}")
            return response.json()
        except APIError as e:
            self._handle_error("get", e)
            return {}

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get an app by name.

        Args:
            name: App name

        Returns:
            App dictionary or None if not found
        """
        apps = self.list()
        for app in apps:
            if app.get("name") == name:
                return app
        return None

    def get_ids(self) -> list[str]:
        """Get all app IDs.

        Returns:
            List of app ID strings (useful for policy statements)
        """
        apps = self.list()
        return [app["id"] for app in apps if "id" in app]
