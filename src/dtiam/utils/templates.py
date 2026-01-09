"""Template utilities for resource creation.

Provides Jinja2-style template rendering for IAM resource definitions.
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any

import yaml
from platformdirs import user_config_dir

# Template variable pattern: {{ variable_name }} or {{ variable_name | default("value") }}
VARIABLE_PATTERN = re.compile(
    r"\{\{\s*(\w+)(?:\s*\|\s*default\s*\(\s*[\"']([^\"']*)[\"']\s*\))?\s*\}\}"
)


class TemplateError(Exception):
    """Exception raised for template errors."""
    pass


class TemplateRenderer:
    """Renders templates with variable substitution.

    Supports Jinja2-style syntax:
        {{ variable }} - required variable
        {{ variable | default("value") }} - variable with default value
    """

    def __init__(self, variables: dict[str, Any] | None = None):
        """Initialize the renderer.

        Args:
            variables: Dictionary of variable name to value mappings
        """
        self.variables = variables or {}

    def render_string(self, template: str) -> str:
        """Render a template string.

        Args:
            template: Template string with {{ variable }} placeholders

        Returns:
            Rendered string with variables substituted

        Raises:
            TemplateError: If a required variable is missing
        """
        missing_vars = []

        def replace_var(match: re.Match) -> str:
            var_name = match.group(1)
            default_value = match.group(2)

            if var_name in self.variables:
                value = self.variables[var_name]
                return str(value) if value is not None else ""

            if default_value is not None:
                return default_value

            missing_vars.append(var_name)
            return match.group(0)  # Keep original placeholder

        result = VARIABLE_PATTERN.sub(replace_var, template)

        if missing_vars:
            raise TemplateError(
                f"Missing required template variables: {', '.join(sorted(set(missing_vars)))}"
            )

        return result

    def render_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Render a dictionary, substituting variables in string values.

        Args:
            data: Dictionary with potential template strings

        Returns:
            Dictionary with variables substituted
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.render_string(value)
            elif isinstance(value, dict):
                result[key] = self.render_dict(value)
            elif isinstance(value, list):
                result[key] = self.render_list(value)
            else:
                result[key] = value
        return result

    def render_list(self, data: list[Any]) -> list[Any]:
        """Render a list, substituting variables in string items.

        Args:
            data: List with potential template strings

        Returns:
            List with variables substituted
        """
        result = []
        for item in data:
            if isinstance(item, str):
                result.append(self.render_string(item))
            elif isinstance(item, dict):
                result.append(self.render_dict(item))
            elif isinstance(item, list):
                result.append(self.render_list(item))
            else:
                result.append(item)
        return result

    def get_variables(self, template: str) -> list[dict[str, Any]]:
        """Extract variable information from a template string.

        Args:
            template: Template string

        Returns:
            List of dicts with 'name' and 'default' (if any) for each variable
        """
        variables = []
        seen = set()

        for match in VARIABLE_PATTERN.finditer(template):
            var_name = match.group(1)
            default_value = match.group(2)

            if var_name not in seen:
                seen.add(var_name)
                var_info = {"name": var_name}
                if default_value is not None:
                    var_info["default"] = default_value
                variables.append(var_info)

        return variables


class TemplateManager:
    """Manages template storage and retrieval."""

    BUILTIN_TEMPLATES = {
        "group-basic": {
            "description": "Basic IAM group",
            "kind": "Group",
            "template": {
                "name": "{{ group_name }}",
                "description": "{{ description | default('') }}",
            },
        },
        "group-team": {
            "description": "Team IAM group with naming convention",
            "kind": "Group",
            "template": {
                "name": "team-{{ team_name }}",
                "description": "IAM group for {{ team_name }} team members",
            },
        },
        "policy-readonly": {
            "description": "Read-only policy for an environment",
            "kind": "Policy",
            "template": {
                "name": "{{ env_name }}-readonly",
                "description": "Read-only access to {{ env_name }} environment",
                "statementQuery": 'ALLOW settings:objects:read, settings:schemas:read WHERE settings:schemaId = "{{ schema_id | default("builtin:*") }}"',
            },
        },
        "policy-admin": {
            "description": "Admin policy for an environment",
            "kind": "Policy",
            "template": {
                "name": "{{ env_name }}-admin",
                "description": "Full admin access to {{ env_name }} environment",
                "statementQuery": "ALLOW settings:objects:read, settings:objects:write, settings:schemas:read",
            },
        },
        "policy-custom": {
            "description": "Custom policy with statement query",
            "kind": "Policy",
            "template": {
                "name": "{{ policy_name }}",
                "description": "{{ description | default('') }}",
                "statementQuery": "{{ statement }}",
            },
        },
        "boundary-zones": {
            "description": "Boundary scoped to management zones",
            "kind": "Boundary",
            "template": {
                "name": "{{ boundary_name }}",
                "description": "Boundary for {{ zone_names }} management zones",
                "boundaryQuery": 'ALLOW environment:* WHERE managementZone.name = "{{ zone_name }}"; ALLOW storage:* WHERE managementZone.name = "{{ zone_name }}"; ALLOW settings:* WHERE managementZone.name = "{{ zone_name }}"',
            },
        },
        "binding-group-policy": {
            "description": "Bind a policy to a group",
            "kind": "Binding",
            "template": {
                "group": "{{ group }}",
                "policy": "{{ policy }}",
                "boundary": "{{ boundary | default('') }}",
            },
        },
        "manifest-team-setup": {
            "description": "Complete team setup with group, policy, and binding",
            "kind": "Manifest",
            "template": {
                "apiVersion": "v1",
                "kind": "List",
                "items": [
                    {
                        "kind": "Group",
                        "spec": {
                            "name": "team-{{ team_name }}",
                            "description": "IAM group for {{ team_name }} team",
                        },
                    },
                    {
                        "kind": "Policy",
                        "spec": {
                            "name": "{{ team_name }}-{{ access_level | default('readonly') }}",
                            "description": "{{ access_level | default('Read-only') }} policy for {{ team_name }}",
                            "statementQuery": "{{ statement | default('ALLOW settings:objects:read, settings:schemas:read') }}",
                        },
                    },
                    {
                        "kind": "Binding",
                        "spec": {
                            "group": "team-{{ team_name }}",
                            "policy": "{{ team_name }}-{{ access_level | default('readonly') }}",
                        },
                    },
                ],
            },
        },
    }

    def __init__(self):
        """Initialize the template manager."""
        self._templates_dir = Path(user_config_dir("dtiam")) / "templates"
        self._ensure_templates_dir()

    def _ensure_templates_dir(self) -> None:
        """Ensure the templates directory exists."""
        self._templates_dir.mkdir(parents=True, exist_ok=True)

    @property
    def templates_dir(self) -> Path:
        """Get the templates directory path."""
        return self._templates_dir

    def list_templates(self, include_builtin: bool = True) -> list[dict[str, Any]]:
        """List all available templates.

        Args:
            include_builtin: Include built-in templates

        Returns:
            List of template info dicts with name, description, kind, source
        """
        templates = []

        # Built-in templates
        if include_builtin:
            for name, template in self.BUILTIN_TEMPLATES.items():
                templates.append({
                    "name": name,
                    "description": template.get("description", ""),
                    "kind": template.get("kind", "Unknown"),
                    "source": "builtin",
                })

        # User templates
        if self._templates_dir.exists():
            for file_path in self._templates_dir.glob("*.yaml"):
                try:
                    content = yaml.safe_load(file_path.read_text())
                    templates.append({
                        "name": file_path.stem,
                        "description": content.get("description", ""),
                        "kind": content.get("kind", "Unknown"),
                        "source": "user",
                    })
                except Exception:
                    pass  # Skip invalid templates

            for file_path in self._templates_dir.glob("*.json"):
                try:
                    content = json.loads(file_path.read_text())
                    templates.append({
                        "name": file_path.stem,
                        "description": content.get("description", ""),
                        "kind": content.get("kind", "Unknown"),
                        "source": "user",
                    })
                except Exception:
                    pass

        return templates

    def get_template(self, name: str) -> dict[str, Any] | None:
        """Get a template by name.

        Args:
            name: Template name

        Returns:
            Template definition or None if not found
        """
        # Check built-in templates first
        if name in self.BUILTIN_TEMPLATES:
            return self.BUILTIN_TEMPLATES[name].copy()

        # Check user templates
        yaml_path = self._templates_dir / f"{name}.yaml"
        if yaml_path.exists():
            return yaml.safe_load(yaml_path.read_text())

        json_path = self._templates_dir / f"{name}.json"
        if json_path.exists():
            return json.loads(json_path.read_text())

        return None

    def save_template(
        self,
        name: str,
        kind: str,
        template: dict[str, Any],
        description: str = "",
    ) -> Path:
        """Save a user template.

        Args:
            name: Template name
            kind: Resource kind (Group, Policy, etc.)
            template: Template definition
            description: Template description

        Returns:
            Path to the saved template file
        """
        template_def = {
            "description": description,
            "kind": kind,
            "template": template,
        }

        file_path = self._templates_dir / f"{name}.yaml"
        file_path.write_text(yaml.dump(template_def, default_flow_style=False))
        return file_path

    def delete_template(self, name: str) -> bool:
        """Delete a user template.

        Args:
            name: Template name

        Returns:
            True if deleted, False if not found or is builtin
        """
        if name in self.BUILTIN_TEMPLATES:
            return False  # Can't delete built-in templates

        yaml_path = self._templates_dir / f"{name}.yaml"
        if yaml_path.exists():
            yaml_path.unlink()
            return True

        json_path = self._templates_dir / f"{name}.json"
        if json_path.exists():
            json_path.unlink()
            return True

        return False

    def get_template_variables(self, name: str) -> list[dict[str, Any]]:
        """Get the variables required by a template.

        Args:
            name: Template name

        Returns:
            List of variable info dicts
        """
        template_def = self.get_template(name)
        if not template_def:
            return []

        template = template_def.get("template", {})
        template_str = yaml.dump(template, default_flow_style=False)

        renderer = TemplateRenderer()
        return renderer.get_variables(template_str)

    def render_template(
        self,
        name: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        """Render a template with the given variables.

        Args:
            name: Template name
            variables: Variable values

        Returns:
            Rendered template

        Raises:
            TemplateError: If template not found or variables missing
        """
        template_def = self.get_template(name)
        if not template_def:
            raise TemplateError(f"Template not found: {name}")

        template = template_def.get("template", {})
        renderer = TemplateRenderer(variables)

        return {
            "kind": template_def.get("kind", "Unknown"),
            "spec": renderer.render_dict(template),
        }
