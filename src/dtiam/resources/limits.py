"""Account limits resource handler for Dynatrace IAM API.

Provides read-only access to account limits and quotas.
"""

from __future__ import annotations

from typing import Any

from dtiam.client import APIError
from dtiam.resources.base import ResourceHandler


class AccountLimitsHandler(ResourceHandler[Any]):
    """Handler for account limits resources.

    Account limits define quotas and restrictions for the account,
    such as maximum users, groups, environments, etc.
    """

    @property
    def resource_name(self) -> str:
        return "limit"

    @property
    def api_path(self) -> str:
        return "/limits"

    @property
    def id_field(self) -> str:
        return "name"

    def list(self, **params: Any) -> list[dict[str, Any]]:
        """List all account limits.

        Returns:
            List of limit dictionaries with name, current value, and max value
        """
        try:
            response = self.client.get(self.api_path, params=params)
            data = response.json()

            if isinstance(data, dict):
                # May be wrapped in items/limits
                return data.get("items", data.get("limits", [data]))
            return data if isinstance(data, list) else []

        except APIError as e:
            self._handle_error("list", e)
            return []

    def get(self, limit_name: str) -> dict[str, Any]:
        """Get a specific limit by name.

        Args:
            limit_name: Name of the limit (e.g., "maxUsers", "maxGroups")

        Returns:
            Limit dictionary or empty dict if not found
        """
        limits = self.list()
        for limit in limits:
            if limit.get("name", "").lower() == limit_name.lower():
                return limit
        return {}

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all limits with usage percentages.

        Returns:
            Dictionary with limits summary and usage statistics
        """
        limits = self.list()

        summary = {
            "limits": [],
            "total_limits": len(limits),
            "limits_near_capacity": 0,
            "limits_at_capacity": 0,
        }

        for limit in limits:
            name = limit.get("name", "unknown")
            current = limit.get("current", limit.get("value", 0))
            maximum = limit.get("max", limit.get("limit", 0))

            # Calculate usage percentage
            if maximum and maximum > 0:
                usage_pct = (current / maximum) * 100
            else:
                usage_pct = 0

            limit_info = {
                "name": name,
                "current": current,
                "max": maximum,
                "usage_percent": round(usage_pct, 1),
                "available": maximum - current if maximum else None,
            }

            # Track capacity warnings
            if usage_pct >= 100:
                limit_info["status"] = "at_capacity"
                summary["limits_at_capacity"] += 1
            elif usage_pct >= 80:
                limit_info["status"] = "near_capacity"
                summary["limits_near_capacity"] += 1
            else:
                limit_info["status"] = "ok"

            summary["limits"].append(limit_info)

        return summary

    def check_capacity(self, limit_name: str, additional: int = 1) -> dict[str, Any]:
        """Check if there's capacity for additional resources.

        Args:
            limit_name: Name of the limit to check
            additional: Number of additional resources needed

        Returns:
            Dictionary with capacity check result
        """
        limit = self.get(limit_name)

        if not limit:
            return {
                "limit_name": limit_name,
                "found": False,
                "has_capacity": None,
                "message": f"Limit '{limit_name}' not found",
            }

        current = limit.get("current", limit.get("value", 0))
        maximum = limit.get("max", limit.get("limit", 0))

        if maximum == 0:
            # Unlimited
            return {
                "limit_name": limit_name,
                "found": True,
                "has_capacity": True,
                "current": current,
                "max": maximum,
                "message": "No limit configured (unlimited)",
            }

        available = maximum - current
        has_capacity = available >= additional

        return {
            "limit_name": limit_name,
            "found": True,
            "has_capacity": has_capacity,
            "current": current,
            "max": maximum,
            "available": available,
            "requested": additional,
            "message": (
                f"Capacity available ({available} remaining)"
                if has_capacity
                else f"Insufficient capacity (need {additional}, have {available})"
            ),
        }
