import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from core.api_version import is_supported_manifest_api_version
from core.runtime import normalize_runtime_target


def normalize_capability_id(value: str | None) -> str:
    if not value:
        return "system"
    return value.strip().replace(":", ".").lower()


def _titleize(value: str) -> str:
    words = value.replace("_", " ").replace("-", " ").replace(".", " ").split()
    return " ".join(word.capitalize() for word in words) or "Value"


def _infer_schema_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "number"
    if isinstance(value, list):
        return "select" if value and all(not isinstance(item, dict) for item in value) else "list"
    if isinstance(value, dict):
        return "group"
    return "text"


def _normalize_schema_field(key: str, value: Any) -> dict[str, Any]:
    if isinstance(value, dict) and ("fields" in value or "type" in value or "key" in value):
        field = dict(value)
        field.setdefault("key", key)
        field.setdefault("label", _titleize(field["key"]))
        field_type = field.get("type") or _infer_schema_type(field.get("default"))
        field["type"] = field_type
        if field_type == "group" or field.get("fields"):
            nested_fields = field.get("fields")
            if not nested_fields:
                nested_fields = [
                    _normalize_schema_field(sub_key, sub_value)
                    for sub_key, sub_value in field.get("default", {}).items()
                ]
            field["fields"] = [
                _normalize_schema_field(
                    sub_field.get("key", f"{field['key']}_field"),
                    sub_field,
                )
                for sub_field in nested_fields
            ]
        options = field.get("options")
        if options and not isinstance(options[0], dict):
            field["options"] = [{"label": str(item), "value": item} for item in options]
        return field

    field_type = _infer_schema_type(value)
    field: dict[str, Any] = {
        "key": key,
        "label": _titleize(key),
        "type": field_type,
    }
    if field_type == "group":
        field["fields"] = [
            _normalize_schema_field(sub_key, sub_value)
            for sub_key, sub_value in value.items()
        ]
    elif field_type == "select":
        field["options"] = [{"label": str(item), "value": item} for item in value]
        if value:
            field["default"] = value[0]
    elif field_type != "list":
        field["default"] = value
    return field


def normalize_config_schema(value: Any) -> dict[str, Any]:
    if not value:
        return {}

    if isinstance(value, dict) and ("fields" in value or ("key" in value and "type" in value)):
        root = dict(value)
        root.setdefault("key", "settings")
        root.setdefault("label", _titleize(root["key"]))
        if root.get("fields"):
            root["fields"] = [
                _normalize_schema_field(field.get("key", f"field_{index}"), field)
                for index, field in enumerate(root["fields"])
            ]
            return root
        return _normalize_schema_field(root["key"], root)

    if isinstance(value, dict):
        return {
            "key": "settings",
            "label": "Settings",
            "fields": [
                _normalize_schema_field(key, field_value)
                for key, field_value in value.items()
            ],
        }

    return {
        "key": "value",
        "label": "Value",
        "type": _infer_schema_type(value),
        "default": value,
    }


def _parse_manifest_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"", "null", "None", "~"}:
        return None
    if value == "{}":
        return {}
    if value == "[]":
        return []
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        return value[1:-1]
    return value


def _read_simple_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        stripped = line.strip()
        if stripped.startswith("- ") and current_list_key:
            data.setdefault(current_list_key, []).append(_parse_manifest_scalar(stripped[2:]))
            continue

        current_list_key = None
        if ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            data[key] = _parse_manifest_scalar(value)
        else:
            data[key] = []
            current_list_key = key

    return data


def read_manifest_file(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    try:
        import yaml

        return yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    except ModuleNotFoundError:
        return _read_simple_yaml(manifest_path)


class CapabilityManifest(BaseModel):
    """
    Unified capability module manifest.

    Stable fields:
    - id
    - api_version
    - kind
    - capability
    - runtime_target
    - config_schema
    - provides
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique capability module identifier")
    name: str | None = Field(default=None, description="Human-readable capability module name")
    description: str | None = Field(default=None, description="Human-readable capability module summary")
    author: str | None = Field(default=None, description="Capability module author")
    api_version: str = Field(default="1.0", description="Stable capability module API version")
    kind: str = Field(default="extension", description="provider | extension | gateway | processor")
    capability: str = Field(default="system", description="Primary capability id")
    runtime_target: str = Field(
        default="main",
        pattern=r"^(main|worker:[a-z0-9_.-]+)$",
        description="Target runtime",
    )
    config_schema: dict[str, Any] = Field(default_factory=dict)
    provides: list[str] = Field(default_factory=list, description="Additional capability ids")
    dependencies: list[str] = Field(default_factory=list)
    entry_point: str | None = Field(default=None)
    min_lumina_version: str | None = Field(default=None)
    runtime: str | None = Field(default=None)
    tags: list[str] = Field(default_factory=list)
    path: str | None = Field(default=None, description="Injected module root path")

    @model_validator(mode="after")
    def validate_api_version(self):
        if not is_supported_manifest_api_version(self.api_version):
            raise ValueError(f"Capability api_version {self.api_version} is not supported by kernel 1.x.")
        return self

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str):
        if not re.match(r"^[a-z0-9_.-]+$", value):
            raise ValueError("Capability id must use lowercase letters, numbers, dots, underscores or dashes.")
        return value

    @field_validator("capability", mode="before")
    @classmethod
    def normalize_capability(cls, value: str):
        return normalize_capability_id(value)

    @field_validator("provides", mode="before")
    @classmethod
    def normalize_provides(cls, values: Any):
        normalized = [normalize_capability_id(item) for item in (values or [])]
        return [item for item in normalized if item]

    @field_validator("runtime_target", mode="before")
    @classmethod
    def normalize_runtime(cls, value: Any):
        return normalize_runtime_target(str(value) if value is not None else None)

    @field_validator("config_schema", mode="before")
    @classmethod
    def normalize_schema(cls, value: Any):
        return normalize_config_schema(value)

    def all_capabilities(self) -> list[str]:
        seen: list[str] = []
        for item in [self.capability, *self.provides]:
            normalized = normalize_capability_id(item)
            if normalized not in seen:
                seen.append(normalized)
        return seen
