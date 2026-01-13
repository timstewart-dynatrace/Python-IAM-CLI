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
                return data.get("boundaries", data.get("items", []))
            return data if isinstance(data, list) else []

        except APIError as e:
            self._handle_error("list", e)
            return []

    def get(self, boundary_id: str) -> dict[str, Any]:
        """Get a single boundary by UUID.

        Args:
            boundary_id: Boundary UUID

        Returns:
            Boundary dictionary
        """
        try:
            response = self.client.get(f"{self.api_path}/{boundary_id}")
            return response.json()
        except APIError as e:
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
            self._handle_error("create", e)
            return {}

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

        Args:
            management_zones: List of management zone names

        Returns:
            Boundary query string
        """
        if not management_zones:
            raise ValueError("At least one management zone is required")

        # Build zone list for IN clause
        zone_list = ', '.join(f'"{zone}"' for zone in management_zones)

        # Standard boundary query structure
        # This restricts environment, storage, and settings access to the zones
        query_parts = [
            f"environment:management-zone IN ({zone_list})",
            f"storage:dt.security_context IN ({zone_list})",
            f"settings:dt.security_context IN ({zone_list})",
        ]

        return "; ".join(query_parts)

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
