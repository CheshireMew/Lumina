import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from core.api_version import check_manifest_compatibility
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


class PluginManifest(BaseModel):
    """
    Unified plugin manifest.

    Stable fields:
    - id
    - api_version
    - kind
    - capability
    - runtime_target
    - permissions
    - config_schema
    - provides
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique plugin identifier")
    api_version: str = Field(default="1.0", description="Stable plugin API version")
    kind: str = Field(default="extension", description="provider | extension | gateway | processor")
    capability: str = Field(default="system", description="Primary capability id")
    runtime_target: str = Field(
        default="main",
        pattern=r"^(main|worker:[a-z0-9_.-]+)$",
        description="Target runtime",
    )
    permissions: list[str] = Field(default_factory=list)
    config_schema: dict[str, Any] = Field(default_factory=dict)
    provides: list[str] = Field(default_factory=list, description="Additional capability ids")
    path: str | None = Field(default=None, description="Injected plugin root path")

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_shape(cls, data: Any):
        if not isinstance(data, dict):
            return data

        raw = dict(data)
        raw.setdefault("api_version", raw.pop("version", "1.0"))
        raw.setdefault("kind", raw.pop("type", raw.pop("category", "extension")))
        raw.setdefault("config_schema", raw.pop("config", raw.pop("settings_schema", {})) or {})

        if "capability" not in raw:
            legacy_group = raw.get("group_id")
            raw["capability"] = legacy_group or raw.get("category") or raw.get("type") or "system"

        raw_provides = raw.get("provides")
        if raw_provides is None:
            raw_provides = raw.pop("capabilities", [])

        normalized_provides: list[str] = []
        for item in raw_provides or []:
            if isinstance(item, str):
                normalized_provides.append(item)
                continue
            if isinstance(item, dict):
                cap_id = item.get("type") or item.get("id")
                if cap_id:
                    normalized_provides.append(cap_id)

        raw["provides"] = normalized_provides
        return raw

    @model_validator(mode="after")
    def validate_api_version(self):
        if not check_manifest_compatibility(self.api_version):
            raise ValueError(f"Plugin api_version {self.api_version} is not compatible with kernel 1.x.")
        return self

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str):
        if not re.match(r"^[a-z0-9_.-]+$", value):
            raise ValueError("Plugin id must use lowercase letters, numbers, dots, underscores or dashes.")
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

    @field_validator("permissions", mode="before")
    @classmethod
    def normalize_permissions(cls, values: Any):
        return [str(item).strip().replace(":", ".") for item in (values or []) if str(item).strip()]

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
