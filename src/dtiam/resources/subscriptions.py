"""Subscription resource handler for Dynatrace Account API.

Provides access to subscription and usage information.
"""

from __future__ import annotations

from typing import Any

from dtiam.client import APIError, Client


class SubscriptionHandler:
    """Handler for subscription resources.

    Subscriptions provide information about account billing,
    usage, and forecasted consumption.

    Note: Uses a different base URL than IAM resources.
    """

    def __init__(self, client: Client):
        self.client = client

    @property
    def base_url(self) -> str:
        """Subscription API base URL."""
        return f"https://api.dynatrace.com/sub/v2/accounts/{self.client.account_uuid}"

    def list(self, **params: Any) -> list[dict[str, Any]]:
        """List all subscriptions for the account.

        Returns:
            List of subscription dictionaries
        """
        try:
            response = self.client.request("GET", f"{self.base_url}/subscriptions", params=params)
            data = response.json()

            if isinstance(data, dict):
                return data.get("items", data.get("subscriptions", [data]))
            return data if isinstance(data, list) else []

        except APIError as e:
            if self.client.verbose:
                print(f"Error listing subscriptions: {e}")
            return []

    def get(self, subscription_uuid: str) -> dict[str, Any]:
        """Get a specific subscription by UUID.

        Args:
            subscription_uuid: Subscription UUID

        Returns:
            Subscription dictionary
        """
        try:
            response = self.client.request(
                "GET",
                f"{self.base_url}/subscriptions/{subscription_uuid}"
            )
            return response.json()
        except APIError as e:
            if self.client.verbose:
                print(f"Error getting subscription: {e}")
            return {}

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get a subscription by name.

        Args:
            name: Subscription name

        Returns:
            Subscription dictionary or None if not found
        """
        subscriptions = self.list()
        for sub in subscriptions:
            if sub.get("name", "").lower() == name.lower():
                return sub
        return None

    def get_forecast(self, subscription_uuid: str | None = None) -> dict[str, Any]:
        """Get usage forecast for subscriptions.

        Args:
            subscription_uuid: Optional specific subscription UUID

        Returns:
            Forecast data dictionary
        """
        try:
            if subscription_uuid:
                path = f"{self.base_url}/subscriptions/{subscription_uuid}/forecast"
            else:
                path = f"{self.base_url}/subscriptions/forecast"

            response = self.client.request("GET", path)
            return response.json()
        except APIError as e:
            if self.client.verbose:
                print(f"Error getting forecast: {e}")
            return {}

    def get_usage(self, subscription_uuid: str) -> dict[str, Any]:
        """Get current usage for a subscription.

        Args:
            subscription_uuid: Subscription UUID

        Returns:
            Usage data dictionary
        """
        sub = self.get(subscription_uuid)
        if not sub:
            return {}

        # Extract usage information from subscription
        return {
            "subscription_uuid": subscription_uuid,
            "name": sub.get("name", ""),
            "type": sub.get("type", ""),
            "status": sub.get("status", ""),
            "start_time": sub.get("startTime", ""),
            "end_time": sub.get("endTime", ""),
            "capabilities": sub.get("capabilities", []),
            "usage": sub.get("currentUsage", sub.get("usage", {})),
        }

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all subscriptions.

        Returns:
            Summary dictionary with subscription statistics
        """
        subscriptions = self.list()

        summary = {
            "total_subscriptions": len(subscriptions),
            "active_subscriptions": 0,
            "subscriptions": [],
        }

        for sub in subscriptions:
            status = sub.get("status", "unknown")
            if status.lower() in ("active", "enabled"):
                summary["active_subscriptions"] += 1

            sub_info = {
                "uuid": sub.get("uuid", sub.get("id", "")),
                "name": sub.get("name", ""),
                "type": sub.get("type", ""),
                "status": status,
                "start_time": sub.get("startTime", ""),
                "end_time": sub.get("endTime", ""),
            }

            # Add usage info if available
            if "currentUsage" in sub or "usage" in sub:
                sub_info["usage"] = sub.get("currentUsage", sub.get("usage", {}))

            summary["subscriptions"].append(sub_info)

        return summary

    def get_capabilities(self, subscription_uuid: str | None = None) -> list[dict[str, Any]]:
        """Get capabilities for subscriptions.

        Args:
            subscription_uuid: Optional specific subscription UUID

        Returns:
            List of capability dictionaries
        """
        if subscription_uuid:
            sub = self.get(subscription_uuid)
            return sub.get("capabilities", []) if sub else []

        # Get capabilities from all subscriptions
        all_capabilities: list[dict[str, Any]] = []
        subscriptions = self.list()

        for sub in subscriptions:
            caps = sub.get("capabilities", [])
            for cap in caps:
                cap_info = dict(cap) if isinstance(cap, dict) else {"name": cap}
                cap_info["subscription"] = sub.get("name", sub.get("uuid", ""))
                all_capabilities.append(cap_info)

        return all_capabilities
