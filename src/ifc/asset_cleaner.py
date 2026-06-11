from __future__ import annotations

from typing import Any

from src.ifc.asset_rules import (
    DIGITAL_TWIN_ASSET_TYPE_BY_IFC_CLASS,
    DIGITAL_TWIN_SYSTEM_ALIASES,
    DIGITAL_TWIN_STATUS_ALIASES,
    DIGITAL_TWIN_SYSTEM_BY_IFC_CLASS,
    DIGITAL_TWIN_SYSTEM_KEYWORDS,
    PLACEHOLDER_VALUES,
)


def _is_placeholder(value: Any) -> bool:
    if not isinstance(value, str):
        return False

    normalized = value.strip().lower()
    return (
        normalized in PLACEHOLDER_VALUES
        or "placeholder" in normalized
        or normalized.startswith("to check")
    )


def _clean_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    stripped = value.strip()
    if not stripped or _is_placeholder(stripped):
        return None

    return stripped


def _normalized_lookup_text(value: str) -> str:
    return " ".join(value.strip().lower().replace("-", " ").replace("_", " ").split())


def _record_change(
    changes: list[dict[str, Any]],
    field: str,
    old_value: Any,
    new_value: Any,
    rule: str,
) -> None:
    if old_value == new_value:
        return

    changes.append(
        {
            "field": field,
            "from": old_value,
            "to": new_value,
            "rule": rule,
        }
    )


def _ensure_properties(asset_data: dict) -> dict:
    properties = asset_data.get("properties")
    if isinstance(properties, dict):
        return properties

    properties = {}
    asset_data["properties"] = properties
    return properties


def _set_asset_field(
    asset_data: dict,
    changes: list[dict[str, Any]],
    field: str,
    value: Any,
    rule: str,
) -> None:
    old_value = asset_data.get(field)
    asset_data[field] = value
    _record_change(changes, field, old_value, value, rule)


def _set_property_field(
    properties: dict,
    changes: list[dict[str, Any]],
    field: str,
    value: Any,
    rule: str,
) -> None:
    old_value = properties.get(field)
    properties[field] = value
    _record_change(changes, field, old_value, value, rule)


def _clean_basic_fields(asset_data: dict, changes: list[dict[str, Any]]) -> None:
    for field in ("asset_code", "global_id", "name", "tag", "floor", "room", "ifc_class"):
        value = _clean_text(asset_data.get(field))
        rule = "CLEAR_PLACEHOLDER" if value is None else "TRIM_TEXT"
        _set_asset_field(asset_data, changes, field, value, rule)

    properties = _ensure_properties(asset_data)
    for field in (
        "asset_identifier",
        "asset_tag",
        "description",
        "equipment_location",
        "equipment_type",
        "functional_location",
        "reference",
        "system_name",
        "manufacturer",
        "model",
        "serial_number",
        "status",
    ):
        value = _clean_text(properties.get(field))
        rule = "CLEAR_PLACEHOLDER" if value is None else "TRIM_TEXT"
        _set_property_field(properties, changes, field, value, rule)


def _promote_digital_twin_fields(asset_data: dict, changes: list[dict[str, Any]]) -> None:
    properties = _ensure_properties(asset_data)

    if not asset_data.get("tag") and properties.get("asset_tag"):
        _set_asset_field(
            asset_data,
            changes,
            "tag",
            properties.get("asset_tag"),
            "PROMOTE_DT_ASSET_TAG",
        )

    if not asset_data.get("name") and properties.get("description"):
        _set_asset_field(
            asset_data,
            changes,
            "name",
            properties.get("description"),
            "PROMOTE_DT_DESCRIPTION_TO_NAME",
        )

    if not asset_data.get("room") and properties.get("equipment_location"):
        _set_asset_field(
            asset_data,
            changes,
            "room",
            properties.get("equipment_location"),
            "PROMOTE_DT_EQUIPMENT_LOCATION",
        )


def _select_asset_code(asset_data: dict, changes: list[dict[str, Any]]) -> None:
    properties = _ensure_properties(asset_data)
    candidates = [
        ("asset_identifier", properties.get("asset_identifier")),
        ("asset_tag", properties.get("asset_tag")),
        ("tag", asset_data.get("tag")),
        ("reference", properties.get("reference")),
        ("global_id", asset_data.get("global_id")),
    ]

    for source, candidate in candidates:
        value = _clean_text(candidate)
        if value:
            _set_asset_field(asset_data, changes, "asset_code", str(value), "SELECT_ASSET_CODE")
            _set_asset_field(
                asset_data,
                changes,
                "asset_code_source",
                source,
                "SELECT_ASSET_CODE_SOURCE",
            )
            return

    _set_asset_field(asset_data, changes, "asset_code", None, "SELECT_ASSET_CODE")
    _set_asset_field(
        asset_data,
        changes,
        "asset_code_source",
        None,
        "SELECT_ASSET_CODE_SOURCE",
    )


def _normalize_asset_type(asset_data: dict, changes: list[dict[str, Any]]) -> None:
    ifc_class = asset_data.get("ifc_class")
    properties = _ensure_properties(asset_data)
    asset_type = _clean_text(properties.get("equipment_type"))

    if asset_type:
        _set_asset_field(
            asset_data,
            changes,
            "asset_type",
            asset_type,
            "MAP_ASSET_TYPE_FROM_DT_PARAMETER",
        )
        return

    mapped_asset_type = DIGITAL_TWIN_ASSET_TYPE_BY_IFC_CLASS.get(ifc_class)
    if mapped_asset_type:
        _set_asset_field(
            asset_data,
            changes,
            "asset_type",
            mapped_asset_type,
            "MAP_ASSET_TYPE_FROM_IFC_CLASS",
        )
    elif ifc_class:
        _set_asset_field(asset_data, changes, "asset_type", ifc_class, "FALLBACK_ASSET_TYPE")


def _system_from_text(value: str | None) -> str | None:
    if not value:
        return None

    normalized = _normalized_lookup_text(value)
    alias = DIGITAL_TWIN_SYSTEM_ALIASES.get(normalized)
    if alias:
        return alias

    code_candidate = normalized.upper()
    if code_candidate in DIGITAL_TWIN_SYSTEM_KEYWORDS:
        return code_candidate

    for system_code, keywords in DIGITAL_TWIN_SYSTEM_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return system_code

    return None


def _normalize_system(asset_data: dict, changes: list[dict[str, Any]]) -> None:
    properties = _ensure_properties(asset_data)
    raw_system = properties.get("system_name") or properties.get("functional_location")
    mapped_system = _system_from_text(raw_system)
    rule = "NORMALIZE_SYSTEM"

    if mapped_system is None:
        mapped_system = DIGITAL_TWIN_SYSTEM_BY_IFC_CLASS.get(asset_data.get("ifc_class"))
        rule = "INFER_SYSTEM_FROM_IFC_CLASS"

    if mapped_system:
        _set_property_field(properties, changes, "system_name", mapped_system, rule)


def _normalize_status(asset_data: dict, changes: list[dict[str, Any]]) -> None:
    properties = _ensure_properties(asset_data)
    raw_status = properties.get("status")

    if not isinstance(raw_status, str):
        return

    normalized = _normalized_lookup_text(raw_status)
    mapped_status = DIGITAL_TWIN_STATUS_ALIASES.get(normalized)
    if mapped_status:
        _set_property_field(
            properties,
            changes,
            "status",
            mapped_status,
            "NORMALIZE_STATUS",
        )


def clean_asset_data(asset_data: dict) -> list[dict[str, Any]]:
    """Clean extracted asset data into the Digital Twin-facing asset shape."""

    changes: list[dict[str, Any]] = []

    _clean_basic_fields(asset_data, changes)
    _promote_digital_twin_fields(asset_data, changes)
    _select_asset_code(asset_data, changes)
    _normalize_asset_type(asset_data, changes)
    _normalize_system(asset_data, changes)
    _normalize_status(asset_data, changes)

    return changes
