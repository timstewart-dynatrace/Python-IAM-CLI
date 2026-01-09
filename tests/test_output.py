"""Tests for the output module."""

from __future__ import annotations

import json
from io import StringIO

import pytest
import yaml

from dtiam.output import (
    OutputFormat,
    Printer,
    Column,
    TableFormatter,
    JSONFormatter,
    YAMLFormatter,
    CSVFormatter,
    PlainFormatter,
)


class TestOutputFormat:
    """Tests for OutputFormat enum."""

    def test_output_formats(self):
        """Test all output format values."""
        assert OutputFormat.TABLE.value == "table"
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.YAML.value == "yaml"
        assert OutputFormat.CSV.value == "csv"
        assert OutputFormat.WIDE.value == "wide"
        assert OutputFormat.PLAIN.value == "plain"


class TestColumn:
    """Tests for Column class."""

    def test_create_column(self):
        """Test creating a column."""
        col = Column("name", "NAME")
        assert col.key == "name"
        assert col.header == "NAME"
        assert col.wide_only is False
        assert col.formatter is not None

    def test_column_with_formatter(self):
        """Test column with formatter."""
        col = Column("status", "STATUS", formatter=lambda x: x.upper())
        assert col.formatter is not None
        assert col.formatter("active") == "ACTIVE"

    def test_column_wide_only(self):
        """Test wide-only column."""
        col = Column("createdAt", "CREATED", wide_only=True)
        assert col.wide_only is True

    def test_column_get_value(self):
        """Test getting value from row."""
        col = Column("name", "NAME")
        row = {"name": "Test", "other": "value"}
        assert col.get_value(row) == "Test"

    def test_column_get_value_missing(self):
        """Test getting missing value from row."""
        col = Column("missing", "MISSING")
        row = {"name": "Test"}
        assert col.get_value(row) == ""

    def test_column_nested_key(self):
        """Test column with nested key."""
        col = Column("user.name", "USER NAME")
        row = {"user": {"name": "John"}}
        assert col.get_value(row) == "John"


class TestTableFormatter:
    """Tests for table formatting."""

    def test_format_simple_table(self):
        """Test formatting a simple table."""
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        columns = [
            Column("name", "NAME"),
            Column("age", "AGE"),
        ]
        formatter = TableFormatter(plain=True)
        result = formatter.format(data, columns)

        assert "NAME" in result
        assert "AGE" in result
        assert "Alice" in result
        assert "Bob" in result

    def test_format_table_with_missing_keys(self):
        """Test table with missing keys in data."""
        data = [
            {"name": "Alice"},
            {"name": "Bob", "age": 25},
        ]
        columns = [
            Column("name", "NAME"),
            Column("age", "AGE"),
        ]
        formatter = TableFormatter(plain=True)
        result = formatter.format(data, columns)

        # Should handle missing keys gracefully
        assert "Alice" in result
        assert "Bob" in result

    def test_format_table_wide_columns(self):
        """Test table with wide columns."""
        data = [{"name": "Test", "extra": "Details"}]
        columns = [
            Column("name", "NAME"),
            Column("extra", "EXTRA", wide_only=True),
        ]

        # Normal mode - wide column hidden
        formatter_normal = TableFormatter(wide=False, plain=True)
        result_normal = formatter_normal.format(data, columns)
        assert "EXTRA" not in result_normal

        # Wide mode - wide column shown
        formatter_wide = TableFormatter(wide=True, plain=True)
        result_wide = formatter_wide.format(data, columns)
        assert "EXTRA" in result_wide

    def test_format_table_with_formatter(self):
        """Test table with column formatter."""
        data = [{"status": "active"}]
        columns = [
            Column("status", "STATUS", formatter=lambda x: x.upper()),
        ]
        formatter = TableFormatter(plain=True)
        result = formatter.format(data, columns)

        assert "ACTIVE" in result

    def test_format_empty_data(self):
        """Test formatting empty data."""
        formatter = TableFormatter()
        result = formatter.format([])
        assert "No resources found" in result


class TestJSONFormatter:
    """Tests for JSON formatting."""

    def test_format_json_list(self):
        """Test formatting a list as JSON."""
        data = [{"name": "Test"}]
        formatter = JSONFormatter()
        result = formatter.format(data)

        parsed = json.loads(result)
        assert parsed == data

    def test_format_json_dict(self):
        """Test formatting a dict as JSON."""
        data = {"name": "Test", "value": 123}
        formatter = JSONFormatter()
        result = formatter.format(data)

        parsed = json.loads(result)
        assert parsed == data

    def test_format_json_pretty(self):
        """Test JSON is formatted with indentation."""
        data = {"name": "Test"}
        formatter = JSONFormatter(indent=2)
        result = formatter.format(data)

        # Should have indentation (newlines)
        assert "\n" in result


class TestYAMLFormatter:
    """Tests for YAML formatting."""

    def test_format_yaml_list(self):
        """Test formatting a list as YAML."""
        data = [{"name": "Test"}]
        formatter = YAMLFormatter()
        result = formatter.format(data)

        parsed = yaml.safe_load(result)
        assert parsed == data

    def test_format_yaml_dict(self):
        """Test formatting a dict as YAML."""
        data = {"name": "Test", "value": 123}
        formatter = YAMLFormatter()
        result = formatter.format(data)

        parsed = yaml.safe_load(result)
        assert parsed == data


class TestCSVFormatter:
    """Tests for CSV formatting."""

    def test_format_csv(self):
        """Test formatting as CSV."""
        data = [
            {"name": "Alice", "age": "30"},
            {"name": "Bob", "age": "25"},
        ]
        columns = [
            Column("name", "NAME"),
            Column("age", "AGE"),
        ]
        formatter = CSVFormatter()
        result = formatter.format(data, columns)

        # CSV uses \r\n line endings on some platforms, so strip and handle
        lines = [line.strip() for line in result.strip().splitlines()]
        assert lines[0] == "NAME,AGE"
        assert "Alice,30" in lines[1]
        assert "Bob,25" in lines[2]

    def test_format_csv_with_commas(self):
        """Test CSV with values containing commas."""
        data = [{"name": "Last, First", "value": "test"}]
        columns = [
            Column("name", "NAME"),
            Column("value", "VALUE"),
        ]
        formatter = CSVFormatter()
        result = formatter.format(data, columns)

        # Should quote the value with comma
        assert '"Last, First"' in result

    def test_format_csv_empty(self):
        """Test CSV with empty data."""
        formatter = CSVFormatter()
        result = formatter.format([])
        assert result == ""


class TestPlainFormatter:
    """Tests for plain text formatting."""

    def test_format_plain_json(self):
        """Test plain formatter outputs JSON."""
        data = {"name": "Test"}
        formatter = PlainFormatter()
        result = formatter.format(data)

        parsed = json.loads(result)
        assert parsed == data


class TestPrinter:
    """Tests for Printer class."""

    def test_printer_table_format(self, capsys):
        """Test printer with table format."""
        printer = Printer(format=OutputFormat.TABLE, plain=False)
        data = [{"name": "Test"}]
        columns = [Column("name", "NAME")]

        printer.print(data, columns)

        captured = capsys.readouterr()
        assert "NAME" in captured.out
        assert "Test" in captured.out

    def test_printer_json_format(self, capsys):
        """Test printer with JSON format."""
        printer = Printer(format=OutputFormat.JSON, plain=False)
        data = [{"name": "Test"}]

        printer.print(data)

        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed == data

    def test_printer_yaml_format(self, capsys):
        """Test printer with YAML format."""
        printer = Printer(format=OutputFormat.YAML, plain=False)
        data = [{"name": "Test"}]

        printer.print(data)

        captured = capsys.readouterr()
        parsed = yaml.safe_load(captured.out)
        assert parsed == data

    def test_printer_format_str(self):
        """Test printer format_str method."""
        printer = Printer(format=OutputFormat.JSON, plain=True)
        data = {"name": "Test"}

        result = printer.format_str(data)

        parsed = json.loads(result)
        assert parsed == data

    def test_printer_plain_mode_overrides_table(self):
        """Test printer in plain mode overrides table format."""
        printer = Printer(format=OutputFormat.TABLE, plain=True)
        # Plain mode should switch table to JSON
        assert printer.format == OutputFormat.JSON

    def test_printer_csv_format(self, capsys):
        """Test printer with CSV format."""
        printer = Printer(format=OutputFormat.CSV, plain=False)
        data = [{"name": "Test", "value": "123"}]
        columns = [Column("name", "NAME"), Column("value", "VALUE")]

        printer.print(data, columns)

        captured = capsys.readouterr()
        assert "NAME,VALUE" in captured.out
        assert "Test,123" in captured.out

