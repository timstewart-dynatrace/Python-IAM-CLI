"""Output formatting for dtiam.

Supports multiple output formats:
- table: ASCII tables (default)
- wide: Extended table with more columns
- json: JSON output
- yaml: YAML output
- csv: CSV output
- plain: Machine-readable output (no colors/formatting)
"""

from __future__ import annotations

import csv
import io
import json
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable

import yaml
from rich.console import Console
from rich.table import Table


class OutputFormat(str, Enum):
    """Supported output formats."""

    TABLE = "table"
    WIDE = "wide"
    JSON = "json"
    YAML = "yaml"
    CSV = "csv"
    PLAIN = "plain"


class Formatter(ABC):
    """Base class for output formatters."""

    @abstractmethod
    def format(self, data: Any, columns: list["Column"] | None = None) -> str:
        """Format data for output."""
        pass


class Column:
    """Column definition for table output."""

    def __init__(
        self,
        key: str,
        header: str,
        wide_only: bool = False,
        formatter: Callable[[Any], str] | None = None,
    ):
        self.key = key
        self.header = header
        self.wide_only = wide_only
        self.formatter = formatter or (lambda x: str(x) if x is not None else "")

    def get_value(self, row: dict[str, Any]) -> str:
        """Extract and format value from a row."""
        # Support nested keys with dot notation
        value = row
        for part in self.key.split("."):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break
        return self.formatter(value)


class TableFormatter(Formatter):
    """Format data as ASCII table using Rich."""

    def __init__(self, wide: bool = False, plain: bool = False):
        self.wide = wide
        self.plain = plain
        self.console = Console(force_terminal=not plain, no_color=plain)

    def format(self, data: Any, columns: list[Column] | None = None) -> str:
        """Format data as a table."""
        if not data:
            return "No resources found."

        # Handle single item
        if isinstance(data, dict):
            data = [data]

        if not columns:
            # Auto-generate columns from first row
            if data:
                columns = [Column(k, k.upper()) for k in data[0].keys()]
            else:
                return "No resources found."

        # Filter columns based on wide mode
        visible_columns = [c for c in columns if not c.wide_only or self.wide]

        table = Table(show_header=True, header_style="bold")

        for col in visible_columns:
            table.add_column(col.header)

        for row in data:
            values = [col.get_value(row) for col in visible_columns]
            table.add_row(*values)

        # Capture table output as string
        with io.StringIO() as buf:
            console = Console(file=buf, force_terminal=not self.plain, no_color=self.plain)
            console.print(table)
            return buf.getvalue()


class JSONFormatter(Formatter):
    """Format data as JSON."""

    def __init__(self, indent: int = 2):
        self.indent = indent

    def format(self, data: Any, columns: list[Column] | None = None) -> str:
        """Format data as indented JSON."""
        return json.dumps(data, indent=self.indent, default=str)


class YAMLFormatter(Formatter):
    """Format data as YAML."""

    def format(self, data: Any, columns: list[Column] | None = None) -> str:
        """Format data as YAML."""
        return yaml.dump(data, default_flow_style=False, sort_keys=False)


class CSVFormatter(Formatter):
    """Format data as CSV."""

    def format(self, data: Any, columns: list[Column] | None = None) -> str:
        """Format data as CSV."""
        if not data:
            return ""

        if isinstance(data, dict):
            data = [data]

        if not columns and data:
            columns = [Column(k, k) for k in data[0].keys()]

        output = io.StringIO()
        if columns:
            writer = csv.writer(output)
            writer.writerow([c.header for c in columns])
            for row in data:
                writer.writerow([c.get_value(row) for c in columns])

        return output.getvalue()


class PlainFormatter(Formatter):
    """Format data as plain text (JSON without colors)."""

    def format(self, data: Any, columns: list[Column] | None = None) -> str:
        """Format data as plain JSON for machine consumption."""
        return json.dumps(data, default=str)


class Printer:
    """Unified printer that handles all output formats."""

    def __init__(
        self,
        format: OutputFormat = OutputFormat.TABLE,
        plain: bool = False,
    ):
        self.format = format
        self.plain = plain

        # Override format if plain mode is enabled
        if plain and format == OutputFormat.TABLE:
            self.format = OutputFormat.JSON

        self._formatters: dict[OutputFormat, Formatter] = {
            OutputFormat.TABLE: TableFormatter(wide=False, plain=plain),
            OutputFormat.WIDE: TableFormatter(wide=True, plain=plain),
            OutputFormat.JSON: JSONFormatter(),
            OutputFormat.YAML: YAMLFormatter(),
            OutputFormat.CSV: CSVFormatter(),
            OutputFormat.PLAIN: PlainFormatter(),
        }

    def print(
        self,
        data: Any,
        columns: list[Column] | None = None,
    ) -> None:
        """Print data in the configured format."""
        formatter = self._formatters[self.format]
        output = formatter.format(data, columns)
        print(output)

    def format_str(
        self,
        data: Any,
        columns: list[Column] | None = None,
    ) -> str:
        """Format data and return as string."""
        formatter = self._formatters[self.format]
        return formatter.format(data, columns)


# Predefined column sets for IAM resources


def group_columns() -> list[Column]:
    """Column definitions for IAM group resources."""
    return [
        Column("uuid", "UUID"),
        Column("name", "NAME"),
        Column("description", "DESCRIPTION"),
        Column("owner", "OWNER", wide_only=True),
        Column("createdAt", "CREATED", wide_only=True),
    ]


def user_columns() -> list[Column]:
    """Column definitions for IAM user resources."""
    return [
        Column("uid", "UID"),
        Column("email", "EMAIL"),
        Column("name", "NAME"),
        Column("userStatus", "STATUS"),
        Column("groups", "GROUPS", wide_only=True, formatter=lambda x: str(len(x)) if x else "0"),
    ]


def policy_columns() -> list[Column]:
    """Column definitions for IAM policy resources."""
    return [
        Column("uuid", "UUID"),
        Column("name", "NAME"),
        Column("description", "DESCRIPTION"),
        Column("levelType", "LEVEL", wide_only=True),
        Column("levelId", "LEVEL ID", wide_only=True),
    ]


def binding_columns() -> list[Column]:
    """Column definitions for IAM policy binding resources."""
    return [
        Column("groupUuid", "GROUP UUID"),
        Column("policyUuid", "POLICY UUID"),
        Column("levelType", "LEVEL TYPE"),
        Column("levelId", "LEVEL ID"),
    ]


def environment_columns() -> list[Column]:
    """Column definitions for environment resources."""
    return [
        Column("id", "ID"),
        Column("name", "NAME"),
        Column("state", "STATE"),
        Column("trial", "TRIAL", formatter=lambda x: "Yes" if x else "No"),
    ]


def boundary_columns() -> list[Column]:
    """Column definitions for IAM boundary resources."""
    return [
        Column("uuid", "UUID"),
        Column("name", "NAME"),
        Column("description", "DESCRIPTION"),
        Column("createdAt", "CREATED", wide_only=True),
    ]


def app_columns() -> list[Column]:
    """Column definitions for App Engine Registry app resources.

    App IDs can be used in policy statements like:
        shared:app-id = '{app.id}';
    """
    return [
        Column("id", "ID"),
        Column("name", "NAME"),
        Column("version", "VERSION"),
        Column("description", "DESCRIPTION", wide_only=True),
    ]


def schema_columns() -> list[Column]:
    """Column definitions for Settings 2.0 schema resources.

    Schema IDs can be used in boundary conditions like:
        settings:schemaId = "builtin:alerting.profile";
    """
    return [
        Column("schemaId", "SCHEMA ID"),
        Column("displayName", "DISPLAY NAME"),
        Column("latestSchemaVersion", "VERSION", wide_only=True),
    ]


def service_user_columns() -> list[Column]:
    """Column definitions for IAM service user (OAuth client) resources."""
    return [
        Column("uid", "UID"),
        Column("name", "NAME"),
        Column("description", "DESCRIPTION"),
        Column(
            "groups",
            "GROUPS",
            wide_only=True,
            formatter=lambda x: str(len(x)) if x else "0",
        ),
    ]


def limit_columns() -> list[Column]:
    """Column definitions for account limit resources."""
    return [
        Column("name", "NAME"),
        Column("current", "CURRENT"),
        Column("max", "MAX"),
        Column(
            "usage_percent",
            "USAGE %",
            wide_only=True,
            formatter=lambda x: f"{x}%" if x is not None else "-",
        ),
    ]


def subscription_columns() -> list[Column]:
    """Column definitions for subscription resources."""
    return [
        Column("uuid", "UUID"),
        Column("name", "NAME"),
        Column("type", "TYPE"),
        Column("status", "STATUS"),
        Column("startTime", "START", wide_only=True),
        Column("endTime", "END", wide_only=True),
    ]


def zone_columns() -> list[Column]:
    """Column definitions for management zone resources (legacy)."""
    return [
        Column("id", "ID"),
        Column("name", "NAME"),
        Column("environmentId", "ENV ID", wide_only=True),
        Column("environmentName", "ENV NAME", wide_only=True),
    ]


def platform_token_columns() -> list[Column]:
    """Column definitions for platform token resources.

    Platform tokens require the `platform-token:tokens:manage` scope.
    """
    return [
        Column("id", "ID"),
        Column("name", "NAME"),
        Column("createdAt", "CREATED"),
        Column("expiresAt", "EXPIRES", wide_only=True),
        Column("lastUsedAt", "LAST USED", wide_only=True),
    ]
