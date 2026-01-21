"""Boundary resource handler for Dynatrace IAM API.

Handles policy boundary CRUD operations for zone-scoped access control.
"""

from __future__ import annotations

from typing import Any

from dtiam.client import APIError
from dtiam.resources.base import ResourceHandler


class BoundaryHandler(ResourceHandler[Any]):
    """Handler for IAM policy boundary resources.

    Boundaries restrict the scope of policies to specific management zones,
    security contexts, or other conditions.
    """

    @property
    def resource_name(self) -> str:
        return "boundary"

    @property
    def api_path(self) -> str:
        # Boundaries use repo path which is NOT under /accounts/{uuid}/
        # Must return full URL since /repo/ is at /iam/v1/repo/, not /iam/v1/accounts/{uuid}/repo/
        return f"https://api.dynatrace.com/iam/v1/repo/account/{self.client.account_uuid}/boundaries"

    @property
    def id_field(self) -> str:
        return "uuid"

    def list(self, **params: Any) -> list[dict[str, Any]]:
        """List all boundaries in the account.

        Args:
            **params: Query parameters for filtering

        Returns:
            List of boundary dictionaries
        """
        try:
            response = self.client.get(self.api_path, params=params)
            data = response.json()

            if isinstance(data, dict):
                # API returns data under "content" key
                return data.get("content", data.get("boundaries", data.get("items", [])))
            return data if isinstance(data, list) else []

        except APIError as e:
            self._handle_error("list", e)
            return []

    def get(self, boundary_id: str) -> dict[str, Any]:
        """Get a single boundary by UUID.

        Note: Falls back to filtering the list if the API doesn't support
        direct GET by UUID (similar to groups endpoint).

        Args:
            boundary_id: Boundary UUID

        Returns:
            Boundary dictionary or empty dict if not found
        """
        try:
            response = self.client.get(f"{self.api_path}/{boundary_id}")
            return response.json()
        except APIError as e:
            if e.status_code == 404:
                # Fall back to filtering the list
                boundaries = self.list()
                for boundary in boundaries:
                    if boundary.get("uuid") == boundary_id:
                        return boundary
                return {}
            self._handle_error("get", e)
            return {}

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get a boundary by name.

        Args:
            name: Boundary name

        Returns:
            Boundary dictionary or None if not found
        """
        boundaries = self.list()
        for boundary in boundaries:
            if boundary.get("name") == name:
                return boundary
        return None

    def create(
        self,
        name: str,
        management_zones: list[str] | None = None,
        boundary_query: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a new policy boundary.

        Args:
            name: Boundary name
            management_zones: List of management zone names to restrict to
            boundary_query: Custom boundary query (overrides management_zones)
            description: Optional description

        Returns:
            Created boundary dictionary
        """
        if not name:
            raise ValueError("Boundary name is required")

        # Build boundary query from management zones if not provided
        if boundary_query is None and management_zones:
            boundary_query = self._build_zone_query(management_zones)
        elif boundary_query is None:
            raise ValueError("Either management_zones or boundary_query is required")

        data: dict[str, Any] = {
            "name": name,
            "boundaryQuery": boundary_query,
        }

        if description:
            data["description"] = description

        try:
            response = self.client.post(self.api_path, json=data)
            return response.json()
        except APIError as e:
            # If boundary already exists, try to return the existing one
            if e.status_code == 400 and e.response_body and "already exists" in e.response_body.lower():
                existing = self.get_by_name(name)
                if existing:
                    return existing
            self._handle_error("create", e)
            return {}

    def create_from_zones(
        self,
        name: str,
        management_zones: list[str],
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a boundary from management zone names.

        Convenience method that builds the boundary query automatically.

        Args:
            name: Boundary name
            management_zones: List of management zone names
            description: Optional description

        Returns:
            Created boundary dictionary
        """
        return self.create(
            name=name,
            management_zones=management_zones,
            description=description,
        )

    def create_from_apps(
        self,
        name: str,
        app_ids: list[str],
        exclude: bool = False,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a boundary from app IDs.

        Convenience method that builds the shared:app-id boundary query.

        Args:
            name: Boundary name
            app_ids: List of app IDs (e.g., "dynatrace.dashboards")
            exclude: If True, use NOT IN instead of IN
            description: Optional description

        Returns:
            Created boundary dictionary
        """
        query = self._build_app_query(app_ids, exclude)
        return self.create(
            name=name,
            boundary_query=query,
            description=description,
        )

    def update(
        self,
        boundary_id: str,
        name: str | None = None,
        management_zones: list[str] | None = None,
        boundary_query: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing boundary.

        Args:
            boundary_id: Boundary UUID
            name: New name (optional)
            management_zones: New management zones (optional)
            boundary_query: New boundary query (optional)
            description: New description (optional)

        Returns:
            Updated boundary dictionary
        """
        # Get current boundary
        current = self.get(boundary_id)
        if not current:
            raise ValueError(f"Boundary {boundary_id} not found")

        data: dict[str, Any] = {
            "name": name or current.get("name"),
            "boundaryQuery": boundary_query or current.get("boundaryQuery"),
        }

        # Build query from zones if provided
        if management_zones:
            data["boundaryQuery"] = self._build_zone_query(management_zones)

        if description is not None:
            data["description"] = description

        try:
            response = self.client.put(f"{self.api_path}/{boundary_id}", json=data)
            return response.json()
        except APIError as e:
            self._handle_error("update", e)
            return {}

    def delete(self, boundary_id: str) -> bool:
        """Delete a boundary.

        Args:
            boundary_id: Boundary UUID

        Returns:
            True if deleted successfully
        """
        try:
            self.client.delete(f"{self.api_path}/{boundary_id}")
            return True
        except APIError as e:
            self._handle_error("delete", e)
            return False

    def _build_zone_query(self, management_zones: list[str]) -> str:
        """Build a boundary query from management zone names.

        The query restricts access to entities within the specified zones.
        Format matches Dynatrace API expectations with semicolons and newlines.

        Args:
            management_zones: List of management zone names

        Returns:
            Boundary query string
        """
        if not management_zones:
            raise ValueError("At least one management zone is required")

        # Build zone list for IN clause
        zone_list = ', '.join(f'"{zone}"' for zone in management_zones)

        # Full boundary query format matching existing boundaries in Dynatrace
        # Uses semicolons with newlines between each clause
        query_parts = [
            f'environment:management-zone IN ({zone_list});',
            f'storage:dt.security_context IN ({zone_list});',
            f'settings:dt.security_context IN ({zone_list});',
        ]

        return "\n".join(query_parts)

    def _build_app_query(self, app_ids: list[str], exclude: bool = False) -> str:
        """Build a boundary query from app IDs.

        Creates a shared:app-id condition to restrict access to specific apps.

        Args:
            app_ids: List of app IDs (e.g., "dynatrace.dashboards")
            exclude: If True, use NOT IN instead of IN

        Returns:
            Boundary query string like: shared:app-id IN ("app1", "app2");
        """
        if not app_ids:
            raise ValueError("At least one app ID is required")

        app_list = ', '.join(f'"{app_id}"' for app_id in app_ids)
        operator = "NOT IN" if exclude else "IN"
        return f'shared:app-id {operator} ({app_list});'

    def _build_schema_query(self, schema_ids: list[str], exclude: bool = False) -> str:
        """Build a boundary query from schema IDs.

        Creates a settings:schemaId condition to restrict access to specific schemas.

        Args:
            schema_ids: List of schema IDs (e.g., "builtin:alerting.profile")
            exclude: If True, use NOT IN instead of IN

        Returns:
            Boundary query string like: settings:schemaId IN ("schema1", "schema2");
        """
        if not schema_ids:
            raise ValueError("At least one schema ID is required")

        schema_list = ', '.join(f'"{schema_id}"' for schema_id in schema_ids)
        operator = "NOT IN" if exclude else "IN"
        return f'settings:schemaId {operator} ({schema_list});'

    def create_from_schemas(
        self,
        name: str,
        schema_ids: list[str],
        exclude: bool = False,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a boundary from schema IDs.

        Convenience method that builds the settings:schemaId boundary query.

        Args:
            name: Boundary name
            schema_ids: List of schema IDs (e.g., "builtin:alerting.profile")
            exclude: If True, use NOT IN instead of IN
            description: Optional description

        Returns:
            Created boundary dictionary
        """
        query = self._build_schema_query(schema_ids, exclude)
        return self.create(
            name=name,
            boundary_query=query,
            description=description,
        )

    def get_attached_policies(self, boundary_id: str) -> list[dict[str, Any]]:
        """Get policies that use this boundary.

        Args:
            boundary_id: Boundary UUID

        Returns:
            List of policy dictionaries
        """
        from dtiam.resources.bindings import BindingHandler

        binding_handler = BindingHandler(self.client)
        all_bindings = binding_handler.list_raw()

        attached_policies = []
        for binding in all_bindings.get("policyBindings", []):
            boundaries = binding.get("boundaries", [])
            if boundary_id in boundaries:
                attached_policies.append({
                    "policyUuid": binding.get("policyUuid"),
                    "groups": binding.get("groups", []),
                })

        return attached_policies
