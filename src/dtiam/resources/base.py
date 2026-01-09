"""Base class for resource handlers.

Provides common functionality for all resource handlers including
CRUD operations and error handling.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from dtiam.client import Client, APIError


T = TypeVar("T", bound=BaseModel)


class ResourceHandler(ABC, Generic[T]):
    """Base class for resource handlers."""

    def __init__(self, client: Client):
        self.client = client

    @property
    @abstractmethod
    def resource_name(self) -> str:
        """Human-readable resource name (e.g., 'group')."""
        pass

    @property
    @abstractmethod
    def api_path(self) -> str:
        """Base API path for this resource."""
        pass

    def _handle_error(self, operation: str, error: APIError) -> None:
        """Handle API errors with descriptive messages."""
        if error.status_code == 404:
            raise ValueError(f"{self.resource_name.title()} not found")
        elif error.status_code == 403:
            raise PermissionError(
                f"Permission denied for {operation} on {self.resource_name}"
            )
        elif error.status_code == 409:
            raise ValueError(f"Conflict: {self.resource_name} already exists or version mismatch")
        else:
            raise RuntimeError(f"Failed to {operation} {self.resource_name}: {error}")


class CRUDHandler(ResourceHandler[T]):
    """Handler with standard CRUD operations."""

    @property
    def list_key(self) -> str:
        """Key in response containing the list of items."""
        return "items"

    @property
    def id_field(self) -> str:
        """Field name for the resource ID."""
        return "uuid"

    def list(self, **params: Any) -> list[dict[str, Any]]:
        """List all resources.

        Args:
            **params: Query parameters for filtering

        Returns:
            List of resource dictionaries
        """
        try:
            response = self.client.get(self.api_path, params=params)
            data = response.json()

            # Handle paginated responses
            if isinstance(data, dict):
                return data.get(self.list_key, data.get("items", []))
            return data if isinstance(data, list) else []

        except APIError as e:
            self._handle_error("list", e)
            return []

    def get(self, resource_id: str) -> dict[str, Any]:
        """Get a single resource by ID.

        Args:
            resource_id: Resource identifier

        Returns:
            Resource dictionary
        """
        try:
            response = self.client.get(f"{self.api_path}/{resource_id}")
            return response.json()
        except APIError as e:
            self._handle_error("get", e)
            return {}

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new resource.

        Args:
            data: Resource data

        Returns:
            Created resource dictionary
        """
        try:
            response = self.client.post(self.api_path, json=data)
            return response.json()
        except APIError as e:
            self._handle_error("create", e)
            return {}

    def update(self, resource_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing resource.

        Args:
            resource_id: Resource identifier
            data: Updated resource data

        Returns:
            Updated resource dictionary
        """
        try:
            response = self.client.put(f"{self.api_path}/{resource_id}", json=data)
            return response.json()
        except APIError as e:
            self._handle_error("update", e)
            return {}

    def delete(self, resource_id: str) -> bool:
        """Delete a resource.

        Args:
            resource_id: Resource identifier

        Returns:
            True if deleted successfully
        """
        try:
            self.client.delete(f"{self.api_path}/{resource_id}")
            return True
        except APIError as e:
            self._handle_error("delete", e)
            return False

    def exists(self, resource_id: str) -> bool:
        """Check if a resource exists.

        Args:
            resource_id: Resource identifier

        Returns:
            True if resource exists
        """
        try:
            self.client.get(f"{self.api_path}/{resource_id}")
            return True
        except APIError:
            return False

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get a resource by name.

        Args:
            name: Resource name

        Returns:
            Resource dictionary or None if not found
        """
        items = self.list()
        for item in items:
            if item.get("name") == name:
                return item
        return None
