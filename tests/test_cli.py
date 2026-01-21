"""Tests for CLI commands and integration."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from dtiam.cli import app, State, state
from dtiam.output import OutputFormat


runner = CliRunner()


class TestCLIBasics:
    """Tests for basic CLI functionality."""

    def test_cli_help(self):
        """Test CLI help output."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "dtiam" in result.output
        assert "kubectl-inspired" in result.output.lower()

    def test_cli_version(self):
        """Test CLI version output."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "dtiam version" in result.output

    def test_cli_no_args(self):
        """Test CLI with no arguments shows help."""
        result = runner.invoke(app, [])
        # Exit code 2 for no args is typical for Typer with no_args_is_help=True
        assert result.exit_code in [0, 2]
        # Should show help content
        assert "dtiam" in result.output or "Usage" in result.output

    def test_cli_invalid_command(self):
        """Test CLI with invalid command."""
        result = runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0


class TestGlobalOptions:
    """Tests for global CLI options."""

    def test_context_option(self):
        """Test --context option is parsed."""
        # We can't fully test this without mocking config, but can verify it's accepted
        result = runner.invoke(app, ["--context", "test", "config", "view"])
        # Should at least parse the option without immediate error
        assert "--context" not in result.output or "unknown" not in result.output.lower()

    def test_output_format_option(self):
        """Test --output option is parsed."""
        result = runner.invoke(app, ["--output", "json", "config", "view"])
        # Should accept the option
        assert "invalid" not in result.output.lower()

    def test_verbose_option(self):
        """Test --verbose option."""
        result = runner.invoke(app, ["--verbose", "config", "view"])
        # Should be accepted
        assert result.exit_code in [0, 1]  # May fail without config but option should work

    def test_plain_option(self):
        """Test --plain option."""
        result = runner.invoke(app, ["--plain", "config", "view"])
        assert result.exit_code in [0, 1]

    def test_dry_run_option(self):
        """Test --dry-run option."""
        result = runner.invoke(app, ["--dry-run", "config", "view"])
        assert result.exit_code in [0, 1]


class TestState:
    """Tests for global State class."""

    def test_state_defaults(self):
        """Test State default values."""
        test_state = State()
        assert test_state.context is None
        assert test_state.output == OutputFormat.TABLE
        assert test_state.verbose is False
        assert test_state.plain is False
        assert test_state.dry_run is False

    def test_state_modification(self):
        """Test State can be modified."""
        test_state = State()
        test_state.context = "test-context"
        test_state.output = OutputFormat.JSON
        test_state.verbose = True
        test_state.plain = True
        test_state.dry_run = True

        assert test_state.context == "test-context"
        assert test_state.output == OutputFormat.JSON
        assert test_state.verbose is True
        assert test_state.plain is True
        assert test_state.dry_run is True


class TestConfigCommands:
    """Tests for config subcommands."""

    def test_config_help(self):
        """Test config command help."""
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "config" in result.output.lower()

    def test_config_view(self):
        """Test config view command."""
        result = runner.invoke(app, ["config", "view"])
        # Will show empty or error, but command should exist
        assert result.exit_code in [0, 1]

    def test_config_current_context(self):
        """Test config current-context command."""
        result = runner.invoke(app, ["config", "current-context"])
        assert result.exit_code in [0, 1]


class TestGetCommands:
    """Tests for get subcommands."""

    def test_get_help(self):
        """Test get command help."""
        result = runner.invoke(app, ["get", "--help"])
        assert result.exit_code == 0
        assert "groups" in result.output.lower()
        assert "users" in result.output.lower()
        assert "policies" in result.output.lower()

    def test_get_groups_help(self):
        """Test get groups help."""
        result = runner.invoke(app, ["get", "groups", "--help"])
        assert result.exit_code == 0


class TestDescribeCommands:
    """Tests for describe subcommands."""

    def test_describe_help(self):
        """Test describe command help."""
        result = runner.invoke(app, ["describe", "--help"])
        assert result.exit_code == 0
        assert "group" in result.output.lower()


class TestCreateCommands:
    """Tests for create subcommands."""

    def test_create_help(self):
        """Test create command help."""
        result = runner.invoke(app, ["create", "--help"])
        assert result.exit_code == 0
        assert "group" in result.output.lower()


class TestDeleteCommands:
    """Tests for delete subcommands."""

    def test_delete_help(self):
        """Test delete command help."""
        result = runner.invoke(app, ["delete", "--help"])
        assert result.exit_code == 0
        assert "group" in result.output.lower()


class TestUserCommands:
    """Tests for user subcommands."""

    def test_user_help(self):
        """Test user command help."""
        result = runner.invoke(app, ["user", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output.lower()
        assert "delete" in result.output.lower()


class TestServiceUserCommands:
    """Tests for service-user subcommands."""

    def test_service_user_help(self):
        """Test service-user command help.

        Note: Basic operations (list, create, delete) have moved to:
        - dtiam get service-users
        - dtiam create service-user
        - dtiam delete service-user

        The service-user subcommand now contains only advanced operations.
        """
        result = runner.invoke(app, ["service-user", "--help"])
        assert result.exit_code == 0
        assert "update" in result.output.lower()
        assert "add-to-group" in result.output.lower()


class TestAccountCommands:
    """Tests for account subcommands."""

    def test_account_help(self):
        """Test account command help."""
        result = runner.invoke(app, ["account", "--help"])
        assert result.exit_code == 0
        assert "limits" in result.output.lower()
        assert "subscriptions" in result.output.lower()


class TestAnalyzeCommands:
    """Tests for analyze subcommands."""

    def test_analyze_help(self):
        """Test analyze command help."""
        result = runner.invoke(app, ["analyze", "--help"])
        assert result.exit_code == 0


class TestBulkCommands:
    """Tests for bulk subcommands."""

    def test_bulk_help(self):
        """Test bulk command help."""
        result = runner.invoke(app, ["bulk", "--help"])
        assert result.exit_code == 0


class TestTemplateCommands:
    """Tests for template subcommands."""

    def test_template_help(self):
        """Test template command help."""
        result = runner.invoke(app, ["template", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output.lower()


class TestExportCommands:
    """Tests for export subcommands."""

    def test_export_help(self):
        """Test export command help."""
        result = runner.invoke(app, ["export", "--help"])
        assert result.exit_code == 0


class TestCacheCommands:
    """Tests for cache subcommands."""

    def test_cache_help(self):
        """Test cache command help."""
        result = runner.invoke(app, ["cache", "--help"])
        assert result.exit_code == 0
        assert "stats" in result.output.lower()
        assert "clear" in result.output.lower()


class TestZonesCommands:
    """Tests for zones subcommands."""

    def test_zones_help(self):
        """Test zones command help."""
        result = runner.invoke(app, ["zones", "--help"])
        assert result.exit_code == 0


class TestGroupCommands:
    """Tests for group subcommands."""

    def test_group_help(self):
        """Test group command help."""
        result = runner.invoke(app, ["group", "--help"])
        assert result.exit_code == 0


class TestBoundaryCommands:
    """Tests for boundary subcommands."""

    def test_boundary_help(self):
        """Test boundary command help."""
        result = runner.invoke(app, ["boundary", "--help"])
        assert result.exit_code == 0



