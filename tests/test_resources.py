"""Tests for resource handlers."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from dtiam.resources.groups import GroupHandler
from dtiam.resources.users import UserHandler
from dtiam.resources.policies import PolicyHandler
from dtiam.resources.bindings import BindingHandler
from dtiam.resources.boundaries import BoundaryHandler
from dtiam.resources.environments import EnvironmentHandler
from dtiam.resources.service_users import ServiceUserHandler
from dtiam.resources.limits import AccountLimitsHandler
from dtiam.resources.subscriptions import SubscriptionHandler
from dtiam.resources.apps import AppHandler


class TestGroupHandler:
    """Tests for GroupHandler."""

    def test_list_groups(self, mock_client, sample_groups, mock_response):
        """Test listing groups."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"items": sample_groups})

            handler = GroupHandler(mock_client)
            groups = handler.list()

            assert len(groups) == 2
            assert groups[0]["name"] == "DevOps Team"
            mock_get.assert_called_once()

    def test_get_group(self, mock_client, sample_groups, mock_response):
        """Test getting a single group."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response(sample_groups[0])

            handler = GroupHandler(mock_client)
            group = handler.get("group-uuid-1")

            assert group["name"] == "DevOps Team"
            assert group["uuid"] == "group-uuid-1"

    def test_get_by_name(self, mock_client, sample_groups, mock_response):
        """Test getting group by name."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"items": sample_groups})

            handler = GroupHandler(mock_client)
            group = handler.get_by_name("Platform Team")

            assert group is not None
            assert group["name"] == "Platform Team"

    def test_get_by_name_not_found(self, mock_client, sample_groups, mock_response):
        """Test getting group by name when not found."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"items": sample_groups})

            handler = GroupHandler(mock_client)
            group = handler.get_by_name("Nonexistent")

            assert group is None

    def test_create_group(self, mock_client, mock_response):
        """Test creating a group."""
        new_group = {"uuid": "new-uuid", "name": "New Group"}
        with patch.object(mock_client, "post") as mock_post:
            mock_post.return_value = mock_response(new_group)

            handler = GroupHandler(mock_client)
            result = handler.create({"name": "New Group"})

            assert result["name"] == "New Group"
            mock_post.assert_called_once()

    def test_delete_group(self, mock_client, mock_response):
        """Test deleting a group."""
        with patch.object(mock_client, "delete") as mock_delete:
            mock_delete.return_value = mock_response(None, status_code=204)

            handler = GroupHandler(mock_client)
            result = handler.delete("group-uuid-1")

            assert result is True
            mock_delete.assert_called_once()


class TestUserHandler:
    """Tests for UserHandler."""

    def test_list_users(self, mock_client, sample_users, mock_response):
        """Test listing users."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"items": sample_users})

            handler = UserHandler(mock_client)
            users = handler.list()

            assert len(users) == 2
            assert users[0]["email"] == "admin@example.com"

    def test_list_users_with_service_users(self, mock_client, sample_users, mock_response):
        """Test listing users including service users."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"items": sample_users})

            handler = UserHandler(mock_client)
            users = handler.list(include_service_users=True)

            # Verify the service-users param was passed
            call_args = mock_get.call_args
            assert call_args[1]["params"]["service-users"] == "true"

    def test_get_by_email(self, mock_client, sample_users, mock_response):
        """Test getting user by email."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"items": sample_users})

            handler = UserHandler(mock_client)
            user = handler.get_by_email("developer@example.com")

            assert user is not None
            assert user["email"] == "developer@example.com"

    def test_create_user(self, mock_client, mock_response):
        """Test creating a user."""
        new_user = {"uid": "new-uid", "email": "new@example.com"}
        with patch.object(mock_client, "post") as mock_post:
            mock_post.return_value = mock_response(new_user)

            handler = UserHandler(mock_client)
            result = handler.create(
                email="new@example.com",
                first_name="New",
                last_name="User",
            )

            assert result["email"] == "new@example.com"
            mock_post.assert_called_once()

    def test_delete_user(self, mock_client, mock_response):
        """Test deleting a user."""
        with patch.object(mock_client, "delete") as mock_delete:
            mock_delete.return_value = mock_response(None, status_code=204)

            handler = UserHandler(mock_client)
            result = handler.delete("user-uid-1")

            assert result is True

    def test_replace_groups(self, mock_client, mock_response):
        """Test replacing user's groups."""
        with patch.object(mock_client, "put") as mock_put:
            mock_put.return_value = mock_response(None, status_code=204)

            handler = UserHandler(mock_client)
            result = handler.replace_groups("user@example.com", ["group-1", "group-2"])

            assert result is True
            mock_put.assert_called_once()
            call_args = mock_put.call_args
            assert "/users/user@example.com/groups" in call_args[0][0]

    def test_remove_from_groups(self, mock_client, mock_response):
        """Test removing user from multiple groups."""
        with patch.object(mock_client, "delete") as mock_delete:
            mock_delete.return_value = mock_response(None, status_code=204)

            handler = UserHandler(mock_client)
            result = handler.remove_from_groups("user@example.com", ["group-1", "group-2"])

            assert result is True
            mock_delete.assert_called_once()

    def test_add_to_groups(self, mock_client, mock_response):
        """Test adding user to multiple groups."""
        with patch.object(mock_client, "post") as mock_post:
            mock_post.return_value = mock_response(None, status_code=204)

            handler = UserHandler(mock_client)
            result = handler.add_to_groups("user@example.com", ["group-1", "group-2"])

            assert result is True
            mock_post.assert_called_once()


class TestBoundaryHandler:
    """Tests for BoundaryHandler."""

    def test_build_zone_query_single_zone(self, mock_client):
        """Test building boundary query with single zone."""
        handler = BoundaryHandler(mock_client)
        query = handler._build_zone_query(["Production"])

        expected = (
            'environment:management-zone IN ("Production");\n'
            'storage:dt.security_context IN ("Production");\n'
            'settings:dt.security_context IN ("Production");'
        )
        assert query == expected

    def test_build_zone_query_multiple_zones(self, mock_client):
        """Test building boundary query with multiple zones."""
        handler = BoundaryHandler(mock_client)
        query = handler._build_zone_query(["Production", "Staging"])

        expected = (
            'environment:management-zone IN ("Production", "Staging");\n'
            'storage:dt.security_context IN ("Production", "Staging");\n'
            'settings:dt.security_context IN ("Production", "Staging");'
        )
        assert query == expected

    def test_create_boundary_with_zones(self, mock_client, mock_response):
        """Test creating boundary with management zones."""
        new_boundary = {"uuid": "boundary-uuid", "name": "Test Boundary"}
        with patch.object(mock_client, "post") as mock_post:
            mock_post.return_value = mock_response(new_boundary)

            handler = BoundaryHandler(mock_client)
            result = handler.create(
                name="Test Boundary",
                management_zones=["Production"],
            )

            assert result["name"] == "Test Boundary"
            # Verify the boundary query was built correctly
            call_args = mock_post.call_args
            assert "boundaryQuery" in call_args[1]["json"]
            assert "environment:management-zone IN" in call_args[1]["json"]["boundaryQuery"]

    def test_list_boundaries(self, mock_client, sample_boundaries, mock_response):
        """Test listing boundaries."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"items": sample_boundaries})

            handler = BoundaryHandler(mock_client)
            boundaries = handler.list()

            assert len(boundaries) == 1
            assert boundaries[0]["name"] == "production-boundary"

    def test_build_app_query_single_app(self, mock_client):
        """Test building app boundary query with single app ID."""
        handler = BoundaryHandler(mock_client)
        query = handler._build_app_query(["dynatrace.dashboards"])

        expected = 'shared:app-id IN ("dynatrace.dashboards");'
        assert query == expected

    def test_build_app_query_multiple_apps(self, mock_client):
        """Test building app boundary query with multiple app IDs."""
        handler = BoundaryHandler(mock_client)
        query = handler._build_app_query([
            "dynatrace.dashboards",
            "dynatrace.logs",
            "dynatrace.notebooks"
        ])

        expected = 'shared:app-id IN ("dynatrace.dashboards", "dynatrace.logs", "dynatrace.notebooks");'
        assert query == expected

    def test_build_app_query_not_in(self, mock_client):
        """Test building app boundary query with NOT IN operator."""
        handler = BoundaryHandler(mock_client)
        query = handler._build_app_query(
            ["dynatrace.classic.smartscape", "dynatrace.classic.custom.applications"],
            exclude=True
        )

        expected = 'shared:app-id NOT IN ("dynatrace.classic.smartscape", "dynatrace.classic.custom.applications");'
        assert query == expected

    def test_build_app_query_empty_raises(self, mock_client):
        """Test that empty app ID list raises ValueError."""
        handler = BoundaryHandler(mock_client)
        with pytest.raises(ValueError, match="At least one app ID is required"):
            handler._build_app_query([])

    def test_create_from_apps(self, mock_client, mock_response):
        """Test creating boundary from app IDs."""
        new_boundary = {"uuid": "app-boundary-uuid", "name": "App Boundary"}
        with patch.object(mock_client, "post") as mock_post:
            mock_post.return_value = mock_response(new_boundary)

            handler = BoundaryHandler(mock_client)
            result = handler.create_from_apps(
                name="App Boundary",
                app_ids=["dynatrace.dashboards", "dynatrace.logs"],
                exclude=False,
            )

            assert result["name"] == "App Boundary"
            # Verify the boundary query was built correctly
            call_args = mock_post.call_args
            assert "boundaryQuery" in call_args[1]["json"]
            assert 'shared:app-id IN ("dynatrace.dashboards", "dynatrace.logs");' in call_args[1]["json"]["boundaryQuery"]


class TestPolicyHandler:
    """Tests for PolicyHandler."""

    def test_list_policies(self, mock_client, sample_policies, mock_response):
        """Test listing policies."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"policies": sample_policies})

            handler = PolicyHandler(mock_client, "account", "abc-123")
            policies = handler.list()

            assert len(policies) == 2
            assert policies[0]["name"] == "admin-policy"

    def test_get_by_name(self, mock_client, sample_policies, mock_response):
        """Test getting policy by name."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"policies": sample_policies})

            handler = PolicyHandler(mock_client, "account", "abc-123")
            policy = handler.get_by_name("viewer-policy")

            assert policy is not None
            assert policy["name"] == "viewer-policy"

    def test_list_aggregate(self, mock_client, sample_policies, mock_response):
        """Test listing aggregate policies."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"policies": sample_policies})

            handler = PolicyHandler(mock_client, "account", "abc-123")
            policies = handler.list_aggregate()

            assert len(policies) == 2
            call_args = mock_get.call_args
            assert "/aggregate" in call_args[0][0]

    def test_validate_policy(self, mock_client, mock_response):
        """Test validating a policy."""
        validation_result = {"valid": True, "errors": []}
        with patch.object(mock_client, "post") as mock_post:
            mock_post.return_value = mock_response(validation_result)

            handler = PolicyHandler(mock_client, "account", "abc-123")
            result = handler.validate({
                "name": "test-policy",
                "statementQuery": "ALLOW settings:objects:read;"
            })

            assert result["valid"] is True
            mock_post.assert_called_once()

    def test_validate_update(self, mock_client, mock_response):
        """Test validating a policy update."""
        validation_result = {"valid": True, "errors": []}
        with patch.object(mock_client, "post") as mock_post:
            mock_post.return_value = mock_response(validation_result)

            handler = PolicyHandler(mock_client, "account", "abc-123")
            result = handler.validate_update("policy-uuid", {
                "statementQuery": "ALLOW settings:objects:write;"
            })

            assert result["valid"] is True
            call_args = mock_post.call_args
            assert "/validation/policy-uuid" in call_args[0][0]


class TestBindingHandler:
    """Tests for BindingHandler."""

    def test_list_bindings(self, mock_client, sample_bindings, mock_response):
        """Test listing bindings."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"policyBindings": sample_bindings})

            handler = BindingHandler(mock_client, "account", "abc-123")
            bindings = handler.list()

            assert len(bindings) == 2

    def test_get_for_group(self, mock_client, mock_response):
        """Test getting bindings for a group."""
        group_bindings = [{"policyUuid": "policy-1", "boundaries": []}]
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"policyBindings": group_bindings})

            handler = BindingHandler(mock_client, "account", "abc-123")
            bindings = handler.get_for_group("group-uuid-1")

            assert len(bindings) == 1

    def test_get_for_policy(self, mock_client, mock_response):
        """Test getting bindings for a policy."""
        policy_binding = {"groups": ["group-1", "group-2"], "boundaries": ["boundary-1"]}
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response(policy_binding)

            handler = BindingHandler(mock_client, "account", "abc-123")
            bindings = handler.get_for_policy("policy-uuid-1")

            assert len(bindings) == 1
            assert bindings[0]["groups"] == ["group-1", "group-2"]

    def test_get_policy_group_binding(self, mock_client, mock_response):
        """Test getting specific policy-group binding."""
        binding = {"boundaries": ["boundary-1"]}
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response(binding)

            handler = BindingHandler(mock_client, "account", "abc-123")
            result = handler.get_policy_group_binding("policy-uuid", "group-uuid")

            assert result["policyUuid"] == "policy-uuid"
            assert result["groupUuid"] == "group-uuid"
            assert result["boundaries"] == ["boundary-1"]

    def test_get_descendants(self, mock_client, mock_response):
        """Test getting descendant bindings."""
        descendant_bindings = [
            {"groups": ["group-1"], "boundaries": [], "levelType": "environment", "levelId": "env-1"}
        ]
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"policyBindings": descendant_bindings})

            handler = BindingHandler(mock_client, "account", "abc-123")
            bindings = handler.get_descendants("policy-uuid")

            assert len(bindings) == 1
            assert bindings[0]["levelType"] == "environment"

    def test_update_group_bindings(self, mock_client, mock_response):
        """Test updating group bindings."""
        with patch.object(mock_client, "put") as mock_put:
            mock_put.return_value = mock_response(None, status_code=204)

            handler = BindingHandler(mock_client, "account", "abc-123")
            result = handler.update_group_bindings(
                "group-uuid",
                [{"policyUuid": "policy-1"}, {"policyUuid": "policy-2"}]
            )

            assert result is True
            mock_put.assert_called_once()


class TestEnvironmentHandler:
    """Tests for EnvironmentHandler."""

    def test_list_environments(self, mock_client, sample_environments, mock_response):
        """Test listing environments."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"tenants": sample_environments})

            handler = EnvironmentHandler(mock_client)
            envs = handler.list()

            assert len(envs) == 2
            assert envs[0]["name"] == "Production"


class TestServiceUserHandler:
    """Tests for ServiceUserHandler."""

    def test_list_service_users(self, mock_client, sample_service_users, mock_response):
        """Test listing service users."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"items": sample_service_users})

            handler = ServiceUserHandler(mock_client)
            users = handler.list()

            assert len(users) == 1
            assert users[0]["name"] == "CI Pipeline"

    def test_create_service_user(self, mock_client, mock_response):
        """Test creating a service user."""
        new_user = {
            "uid": "new-su-uid",
            "name": "New Service User",
            "clientId": "dt0s01.NEWCLIENT",
            "clientSecret": "dt0s01.NEWCLIENT.SECRET",
        }
        with patch.object(mock_client, "post") as mock_post:
            mock_post.return_value = mock_response(new_user)

            handler = ServiceUserHandler(mock_client)
            result = handler.create(name="New Service User")

            assert result["name"] == "New Service User"
            assert "clientId" in result
            assert "clientSecret" in result

    def test_get_by_name(self, mock_client, sample_service_users, mock_response):
        """Test getting service user by name."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"items": sample_service_users})

            handler = ServiceUserHandler(mock_client)
            user = handler.get_by_name("CI Pipeline")

            assert user is not None
            assert user["name"] == "CI Pipeline"


class TestAccountLimitsHandler:
    """Tests for AccountLimitsHandler."""

    def test_list_limits(self, mock_client, sample_limits, mock_response):
        """Test listing limits."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"items": sample_limits})

            handler = AccountLimitsHandler(mock_client)
            limits = handler.list()

            assert len(limits) == 3

    def test_get_limit(self, mock_client, sample_limits, mock_response):
        """Test getting a specific limit."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"items": sample_limits})

            handler = AccountLimitsHandler(mock_client)
            limit = handler.get("maxUsers")

            assert limit["name"] == "maxUsers"
            assert limit["current"] == 50
            assert limit["max"] == 100

    def test_get_summary(self, mock_client, sample_limits, mock_response):
        """Test getting limits summary."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"items": sample_limits})

            handler = AccountLimitsHandler(mock_client)
            summary = handler.get_summary()

            assert summary["total_limits"] == 3
            assert len(summary["limits"]) == 3
            # Check usage percentage calculation
            for limit in summary["limits"]:
                if limit["name"] == "maxUsers":
                    assert limit["usage_percent"] == 50.0

    def test_check_capacity_available(self, mock_client, sample_limits, mock_response):
        """Test checking capacity when available."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"items": sample_limits})

            handler = AccountLimitsHandler(mock_client)
            result = handler.check_capacity("maxUsers", additional=10)

            assert result["has_capacity"] is True
            assert result["available"] == 50

    def test_check_capacity_insufficient(self, mock_client, sample_limits, mock_response):
        """Test checking capacity when insufficient."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"items": sample_limits})

            handler = AccountLimitsHandler(mock_client)
            result = handler.check_capacity("maxUsers", additional=100)

            assert result["has_capacity"] is False


class TestSubscriptionHandler:
    """Tests for SubscriptionHandler."""

    def test_list_subscriptions(self, mock_client, sample_subscriptions, mock_response):
        """Test listing subscriptions."""
        with patch.object(mock_client, "request") as mock_request:
            mock_request.return_value = mock_response({"items": sample_subscriptions})

            handler = SubscriptionHandler(mock_client)
            subs = handler.list()

            assert len(subs) == 1
            assert subs[0]["name"] == "Enterprise"

    def test_get_summary(self, mock_client, sample_subscriptions, mock_response):
        """Test getting subscriptions summary."""
        with patch.object(mock_client, "request") as mock_request:
            mock_request.return_value = mock_response({"items": sample_subscriptions})

            handler = SubscriptionHandler(mock_client)
            summary = handler.get_summary()

            assert summary["total_subscriptions"] == 1
            assert summary["active_subscriptions"] == 1

    def test_get_by_name(self, mock_client, sample_subscriptions, mock_response):
        """Test getting subscription by name."""
        with patch.object(mock_client, "request") as mock_request:
            mock_request.return_value = mock_response({"items": sample_subscriptions})

            handler = SubscriptionHandler(mock_client)
            sub = handler.get_by_name("Enterprise")

            assert sub is not None
            assert sub["name"] == "Enterprise"


class TestAppHandler:
    """Tests for AppHandler."""

    @pytest.fixture
    def sample_apps(self) -> list[dict[str, Any]]:
        """Sample app data for testing."""
        return [
            {"id": "dynatrace.dashboards", "name": "Dashboards"},
            {"id": "dynatrace.logs", "name": "Logs"},
            {"id": "dynatrace.notebooks", "name": "Notebooks"},
            {"id": "dynatrace.classic.smartscape", "name": "Smartscape"},
        ]

    def test_list_apps(self, mock_client, mock_response):
        """Test listing apps."""
        apps = [
            {"id": "dynatrace.dashboards", "name": "Dashboards"},
            {"id": "dynatrace.logs", "name": "Logs"},
        ]
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"apps": apps})

            handler = AppHandler(mock_client, "https://abc12345.apps.dynatrace.com")
            result = handler.list()

            assert len(result) == 2
            assert result[0]["id"] == "dynatrace.dashboards"

    def test_get_ids(self, mock_client, mock_response, sample_apps):
        """Test getting app IDs."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"apps": sample_apps})

            handler = AppHandler(mock_client, "https://abc12345.apps.dynatrace.com")
            ids = handler.get_ids()

            assert len(ids) == 4
            assert "dynatrace.dashboards" in ids
            assert "dynatrace.logs" in ids

    def test_validate_app_ids_all_valid(self, mock_client, mock_response, sample_apps):
        """Test validating app IDs when all are valid."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"apps": sample_apps})

            handler = AppHandler(mock_client, "https://abc12345.apps.dynatrace.com")
            valid, invalid = handler.validate_app_ids([
                "dynatrace.dashboards",
                "dynatrace.logs"
            ])

            assert valid == ["dynatrace.dashboards", "dynatrace.logs"]
            assert invalid == []

    def test_validate_app_ids_some_invalid(self, mock_client, mock_response, sample_apps):
        """Test validating app IDs when some are invalid."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"apps": sample_apps})

            handler = AppHandler(mock_client, "https://abc12345.apps.dynatrace.com")
            valid, invalid = handler.validate_app_ids([
                "dynatrace.dashboards",
                "invalid.app.one",
                "dynatrace.logs",
                "invalid.app.two"
            ])

            assert valid == ["dynatrace.dashboards", "dynatrace.logs"]
            assert invalid == ["invalid.app.one", "invalid.app.two"]

    def test_validate_app_ids_all_invalid(self, mock_client, mock_response, sample_apps):
        """Test validating app IDs when all are invalid."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"apps": sample_apps})

            handler = AppHandler(mock_client, "https://abc12345.apps.dynatrace.com")
            valid, invalid = handler.validate_app_ids([
                "totally.fake.app",
                "another.fake.app"
            ])

            assert valid == []
            assert invalid == ["totally.fake.app", "another.fake.app"]

    def test_validate_app_ids_preserves_order(self, mock_client, mock_response, sample_apps):
        """Test that validation preserves original order."""
        with patch.object(mock_client, "get") as mock_get:
            mock_get.return_value = mock_response({"apps": sample_apps})

            handler = AppHandler(mock_client, "https://abc12345.apps.dynatrace.com")
            valid, invalid = handler.validate_app_ids([
                "dynatrace.notebooks",
                "invalid.one",
                "dynatrace.dashboards",
                "invalid.two",
                "dynatrace.logs"
            ])

            # Order should match input order for valid/invalid respectively
            assert valid == ["dynatrace.notebooks", "dynatrace.dashboards", "dynatrace.logs"]
            assert invalid == ["invalid.one", "invalid.two"]
