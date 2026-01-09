"""Resource resolver utilities.

Provides smart resolution of resource identifiers (UUID vs name).
"""

from __future__ import annotations

import re
from typing import Any

from dtiam.client import Client


# UUID pattern for Dynatrace resources
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Short ID pattern (some resources use shorter IDs)
SHORT_ID_PATTERN = re.compile(r"^[0-9a-f]{16,}$", re.IGNORECASE)


def is_uuid(value: str) -> bool:
    """Check if a string looks like a UUID."""
    return bool(UUID_PATTERN.match(value))


def is_likely_id(value: str) -> bool:
    """Check if a string is likely an ID rather than a name.

    Uses heuristics:
    - UUID format
    - All hex characters and longer than 16 chars
    - No spaces
    """
    if is_uuid(value):
        return True
    if SHORT_ID_PATTERN.match(value):
        return True
    # Names typically have spaces or are human-readable
    return False


class ResourceResolver:
    """Resolves resource identifiers to UUIDs.

    Supports resolution by:
    - UUID (returned as-is)
    - Name (looked up via API)
    """

    def __init__(self, client: Client):
        self.client = client

    def resolve_group(self, identifier: str) -> str:
        """Resolve a group identifier to its UUID.

        Args:
            identifier: Group UUID or name

        Returns:
            Group UUID

        Raises:
            ValueError: If group not found
        """
        from dtiam.resources.groups import GroupHandler

        handler = GroupHandler(self.client)

        # Try as UUID first if it looks like one
        if is_likely_id(identifier):
            group = handler.get(identifier)
            if group:
                return group.get("uuid", identifier)

        # Try by name
        group = handler.get_by_name(identifier)
        if group:
            return group.get("uuid", "")

        # If it looks like an ID, return it (API will validate)
        if is_likely_id(identifier):
            return identifier

        raise ValueError(f"Group not found: {identifier}")

    def resolve_user(self, identifier: str) -> str:
        """Resolve a user identifier to its UID.

        Args:
            identifier: User UID or email

        Returns:
            User UID

        Raises:
            ValueError: If user not found
        """
        from dtiam.resources.users import UserHandler

        handler = UserHandler(self.client)

        # If it looks like an email, search by email
        if "@" in identifier:
            user = handler.get_by_email(identifier)
            if user:
                return user.get("uid", "")
            raise ValueError(f"User not found: {identifier}")

        # Try as UID
        user = handler.get(identifier)
        if user:
            return user.get("uid", identifier)

        raise ValueError(f"User not found: {identifier}")

    def resolve_policy(
        self,
        identifier: str,
        level_type: str = "account",
        level_id: str | None = None,
    ) -> str:
        """Resolve a policy identifier to its UUID.

        Args:
            identifier: Policy UUID or name
            level_type: Policy level (account, global)
            level_id: Level identifier

        Returns:
            Policy UUID

        Raises:
            ValueError: If policy not found
        """
        from dtiam.resources.policies import PolicyHandler

        handler = PolicyHandler(
            self.client,
            level_type=level_type,  # type: ignore
            level_id=level_id or self.client.account_uuid,
        )

        # Try as UUID first if it looks like one
        if is_likely_id(identifier):
            policy = handler.get(identifier)
            if policy:
                return policy.get("uuid", identifier)

        # Try by name
        policy = handler.get_by_name(identifier)
        if policy:
            return policy.get("uuid", "")

        # If it looks like an ID, return it (API will validate)
        if is_likely_id(identifier):
            return identifier

        raise ValueError(f"Policy not found: {identifier}")

    def resolve_environment(self, identifier: str) -> str:
        """Resolve an environment identifier to its ID.

        Args:
            identifier: Environment ID or name

        Returns:
            Environment ID

        Raises:
            ValueError: If environment not found
        """
        from dtiam.resources.environments import EnvironmentHandler

        handler = EnvironmentHandler(self.client)

        # Try as ID first
        env = handler.get(identifier)
        if env:
            return env.get("id", identifier)

        # Try by name
        env = handler.get_by_name(identifier)
        if env:
            return env.get("id", "")

        raise ValueError(f"Environment not found: {identifier}")
