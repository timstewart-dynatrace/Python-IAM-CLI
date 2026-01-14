"""Settings Schema resource handler for Dynatrace Environment API.

Handles listing Settings 2.0 schemas from the Environment API.
Schema IDs can be used in boundary conditions like:
    settings:schemaId = "builtin:alerting.profile";
"""

from __future__ import annotations

from typing import Any

from dtiam.client import APIError
from dtiam.resources.base import ResourceHandler


class SchemaHandler(ResourceHandler[Any]):
    """Handler for Dynatrace Settings 2.0 schema resources.

    Schemas are retrieved from environment-specific endpoints.
    Requires an environment URL (e.g., https://{env-id}.live.dynatrace.com)
    and an environment API token with settings.read scope.
    """

    def __init__(self, client: Any, environment_url: str):
        """Initialize the schema handler.

        Args:
            client: HTTP client for making requests
            environment_url: Base URL for the environment
                (e.g., https://abc12345.live.dynatrace.com)
        """
        super().__init__(client)
        # Normalize the environment URL
        self.environment_url = environment_url.rstrip("/")
        if not self.environment_url.startswith("http"):
            self.environment_url = f"https://{self.environment_url}"

    @property
    def resource_name(self) -> str:
        return "schema"

    @property
    def api_path(self) -> str:
        return f"{self.environment_url}/api/v2/settings/schemas"

    @property
    def id_field(self) -> str:
        return "schemaId"

    def list(self, **params: Any) -> list[dict[str, Any]]:
        """List all settings schemas from the Environment API.

        Args:
            **params: Query parameters for filtering

        Returns:
            List of schema dictionaries with schemaId, displayName, etc.
        """
        try:
            response = self.client.get(
                self.api_path,
                params=params,
                use_environment_token=True,
            )
            data = response.json()

            if isinstance(data, dict):
                # API returns schemas under "items" key
                return data.get("items", data.get("schemas", []))
            return data if isinstance(data, list) else []

        except APIError as e:
            self._handle_error("list", e)
            return []

    def get(self, schema_id: str) -> dict[str, Any]:
        """Get a single schema by ID.

        Args:
            schema_id: Schema ID (e.g., "builtin:alerting.profile")

        Returns:
            Schema dictionary with full schema definition
        """
        try:
            response = self.client.get(
                f"{self.api_path}/{schema_id}",
                use_environment_token=True,
            )
            return response.json()
        except APIError as e:
            self._handle_error("get", e)
            return {}

    def get_by_name(self, display_name: str) -> dict[str, Any] | None:
        """Get a schema by display name.

        Args:
            display_name: Schema display name

        Returns:
            Schema dictionary or None if not found
        """
        schemas = self.list()
        for schema in schemas:
            if schema.get("displayName") == display_name:
                return schema
        return None

    def get_ids(self) -> list[str]:
        """Get all schema IDs.

        Returns:
            List of schema ID strings (useful for boundary conditions)
        """
        schemas = self.list()
        return [schema["schemaId"] for schema in schemas if "schemaId" in schema]

    def get_builtin_ids(self) -> list[str]:
        """Get all builtin schema IDs (starting with 'builtin:').

        Returns:
            List of builtin schema ID strings
        """
        return [sid for sid in self.get_ids() if sid.startswith("builtin:")]

    def validate_schema_ids(self, schema_ids: list[str]) -> tuple[list[str], list[str]]:
        """Validate schema IDs against the environment.

        Checks if the provided schema IDs exist in the Settings API.

        Args:
            schema_ids: List of schema IDs to validate

        Returns:
            Tuple of (valid_ids, invalid_ids) preserving original order
        """
        known_ids = set(self.get_ids())
        valid = [sid for sid in schema_ids if sid in known_ids]
        invalid = [sid for sid in schema_ids if sid not in known_ids]
        return valid, invalid

    def search(self, pattern: str) -> list[dict[str, Any]]:
        """Search schemas by ID or display name pattern.

        Args:
            pattern: Search pattern (case-insensitive substring match)

        Returns:
            List of matching schema dictionaries
        """
        schemas = self.list()
        pattern_lower = pattern.lower()
        return [
            s for s in schemas
            if pattern_lower in s.get("schemaId", "").lower()
            or pattern_lower in s.get("displayName", "").lower()
        ]
