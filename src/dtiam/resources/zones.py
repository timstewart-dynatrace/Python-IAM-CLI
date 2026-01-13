"""Management Zone resource handler for Dynatrace API.

Handles management zone operations via the Dynatrace Environment API.

DEPRECATION NOTICE: Management Zone features are provided for legacy purposes only
and will be removed in a future release. Dynatrace is transitioning away from
management zones in favor of other access control mechanisms.
"""

from __future__ import annotations

from typing import Any

from dtiam.client import Client, APIError
from dtiam.resources.base import ResourceHandler


class ZoneHandler(ResourceHandler[Any]):
    """Handler for management zone resources.

    Management zones are accessed via the Dynatrace Environment API,
    not the Account Management API.
    """

    def __init__(self, client: Client, environment_url: str | None = None):
        """Initialize the zone handler.

        Args:
            client: API client
            environment_url: Optional environment URL override
        """
        super().__init__(client)
        self.environment_url = environment_url

    @property
    def resource_name(self) -> str:
        return "zone"

    @property
    def api_path(self) -> str:
        return "/api/config/v1/managementZones"

    @property
    def id_field(self) -> str:
        return "id"

    def list(self, environment_id: str | None = None, **params: Any) -> list[dict[str, Any]]:
        """List all management zones.

        Args:
            environment_id: Optional environment ID to query
            **params: Query parameters

        Returns:
            List of zone dictionaries with id, name, rules
        """
        try:
            # Management zones require an environment URL
            if not self.environment_url:
                raise RuntimeError(
                    "Management zones require an environment URL. "
                    "Set DTIAM_ENVIRONMENT_URL environment variable or "
                    "configure environment-url in credentials."
                )

            # Build the full URL for the environment API
            url = self.environment_url.rstrip('/')
            if not url.startswith('http'):
                # Assume it's an environment ID and construct the URL
                url = f"https://{url}.live.dynatrace.com"

            response = self.client.request(
                "GET",
                f"{url}{self.api_path}",
                use_environment_token=True,
                params=params
            )
            data = response.json()

            if isinstance(data, dict):
                return data.get("values", data.get("items", []))
            return data if isinstance(data, list) else []

        except APIError as e:
            self._handle_error("list", e)
            return []

    def get(self, zone_id: str) -> dict[str, Any]:
        """Get a management zone by ID.

        Args:
            zone_id: Zone ID

        Returns:
            Zone dictionary
        """
        try:
            if not self.environment_url:
                raise RuntimeError(
                    "Management zones require an environment URL. "
                    "Set DTIAM_ENVIRONMENT_URL environment variable or "
                    "configure environment-url in credentials."
                )

            # Build the full URL for the environment API
            url = self.environment_url.rstrip('/')
            if not url.startswith('http'):
                # Assume it's an environment ID and construct the URL
                url = f"https://{url}.live.dynatrace.com"

            response = self.client.request(
                "GET",
                f"{url}{self.api_path}/{zone_id}",
                use_environment_token=True
            )
            return response.json()
        except APIError as e:
            self._handle_error("get", e)
            return {}

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get a zone by name.

        Args:
            name: Zone name

        Returns:
            Zone dictionary or None
        """
        zones = self.list()
        for zone in zones:
            if zone.get("name", "").lower() == name.lower():
                return zone
        return None

    def list_from_account(self) -> list[dict[str, Any]]:
        """List zones from all environments in the account.

        Returns:
            List of zone dictionaries with environment info
        """
        from dtiam.resources.environments import EnvironmentHandler

        env_handler = EnvironmentHandler(self.client)
        environments = env_handler.list()

        all_zones = []
        for env in environments:
            env_id = env.get("id", "")
            env_name = env.get("name", "")
            env_url = env.get("managementZoneUrl") or env.get("url", "")

            if env_url:
                try:
                    zone_handler = ZoneHandler(self.client, environment_url=env_url)
                    zones = zone_handler.list()
                    for zone in zones:
                        zone["environmentId"] = env_id
                        zone["environmentName"] = env_name
                    all_zones.extend(zones)
                except Exception:
                    pass  # Skip environments we can't access

        return all_zones

    def compare_with_groups(
        self,
        groups: list[dict[str, Any]],
        case_sensitive: bool = False,
    ) -> dict[str, Any]:
        """Compare zone names with group names.

        Args:
            groups: List of group dictionaries
            case_sensitive: Whether to use case-sensitive matching

        Returns:
            Dictionary with matched, unmatched_zones, unmatched_groups
        """
        zones = self.list()

        zone_names = {z.get("name", "") for z in zones}
        group_names = {g.get("name", "") for g in groups}

        if not case_sensitive:
            zone_names_lower = {n.lower(): n for n in zone_names}
            group_names_lower = {n.lower(): n for n in group_names}

            matched = []
            for lower_name, zone_name in zone_names_lower.items():
                if lower_name in group_names_lower:
                    matched.append({
                        "zone_name": zone_name,
                        "group_name": group_names_lower[lower_name],
                    })

            matched_zone_names = {m["zone_name"].lower() for m in matched}
            matched_group_names = {m["group_name"].lower() for m in matched}

            unmatched_zones = [n for n in zone_names if n.lower() not in matched_zone_names]
            unmatched_groups = [n for n in group_names if n.lower() not in matched_group_names]
        else:
            matched_names = zone_names & group_names
            matched = [{"zone_name": n, "group_name": n} for n in matched_names]
            unmatched_zones = list(zone_names - matched_names)
            unmatched_groups = list(group_names - matched_names)

        return {
            "matched": matched,
            "matched_count": len(matched),
            "unmatched_zones": sorted(unmatched_zones),
            "unmatched_zones_count": len(unmatched_zones),
            "unmatched_groups": sorted(unmatched_groups),
            "unmatched_groups_count": len(unmatched_groups),
        }
