from collections.abc import Mapping
from typing import Any

from src.ifc.asset_rules import (
    DIGITAL_TWIN_STATUS_VALUES,
    PLACEHOLDER_VALUES,
    SERVICEABLE_IFC_CLASSES,
    SYSTEM_REQUIRED_IFC_CLASSES,
)
from src.models.enums import ValidationSeverity, ValidationStage


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _is_placeholder(value: Any) -> bool:
    if not isinstance(value, str):
        return False

    normalized = value.strip().lower()
    return normalized in PLACEHOLDER_VALUES


def _field_value(asset_data: dict, field: str) -> Any:
    if field in asset_data:
        return asset_data.get(field)

    properties = asset_data.get("properties")
    if isinstance(properties, Mapping):
        return properties.get(field)

    return None


def _issue(
    code: str,
    field: str,
    message: str,
    severity: ValidationSeverity = ValidationSeverity.WARNING,
    stage: ValidationStage = ValidationStage.ASSET_VALIDATION,
) -> dict:
    return {
        "stage": stage,
        "severity": severity,
        "code": code,
        "field": field,
        "message": message,
    }


def _check_required_fields(asset_data: dict) -> list[dict]:
    checks = [
        (
            "global_id",
            ValidationSeverity.ERROR,
            "MISSING_GLOBAL_ID",
            "Asset is missing GlobalId.",
        ),
        (
            "name",
            ValidationSeverity.WARNING,
            "MISSING_NAME",
            "Asset is missing Name.",
        ),
        (
            "asset_code",
            ValidationSeverity.ERROR,
            "MISSING_ASSET_CODE",
            "Asset is missing asset code.",
        ),
        (
            "ifc_class",
            ValidationSeverity.ERROR,
            "MISSING_IFC_CLASS",
            "Asset is missing IFC class.",
        ),
        (
            "floor",
            ValidationSeverity.WARNING,
            "MISSING_FLOOR",
            "Asset is missing floor.",
        ),
        (
            "room",
            ValidationSeverity.WARNING,
            "MISSING_ROOM",
            "Asset is missing room.",
        ),
    ]

    issues = []
    for field, severity, code, message in checks:
        if _is_blank(_field_value(asset_data, field)):
            issues.append(_issue(code, field, message, severity))

    return issues


def _check_placeholder_values(asset_data: dict) -> list[dict]:
    issues = []
    for field in (
        "asset_code",
        "name",
        "tag",
        "floor",
        "room",
        "system_name",
        "manufacturer",
        "model",
        "serial_number",
        "status",
    ):
        value = _field_value(asset_data, field)
        if _is_placeholder(value):
            issues.append(
                _issue(
                    "PLACEHOLDER_VALUE",
                    field,
                    f"Asset field {field} contains placeholder value.",
                )
            )

    return issues


def _check_operational_name(asset_data: dict) -> list[dict]:
    name = _field_value(asset_data, "name")
    if not isinstance(name, str):
        return []

    normalized = name.strip().lower()
    if not normalized:
        return []

    if normalized in {"default", "unnamed", "unknown"} or normalized.startswith("default "):
        return [
            _issue(
                "NON_OPERATIONAL_NAME",
                "name",
                "Asset name looks like a placeholder or non-operational family name.",
            )
        ]

    return []


def _check_asset_code_source(asset_data: dict) -> list[dict]:
    if asset_data.get("asset_code_source") != "global_id":
        return []

    return [
        _issue(
            "ASSET_CODE_FALLBACK_GLOBAL_ID",
            "asset_code",
            "Asset code is temporarily using GlobalId and should be standardized.",
        )
    ]


def _check_system(asset_data: dict) -> list[dict]:
    ifc_class = asset_data.get("ifc_class")
    if ifc_class not in SYSTEM_REQUIRED_IFC_CLASSES:
        return []

    if _is_blank(_field_value(asset_data, "system_name")):
        return [
            _issue(
                "MISSING_SYSTEM",
                "system_name",
                "System asset is missing system name.",
                ValidationSeverity.ERROR,
            )
        ]

    return []


def _check_maintenance_fields(asset_data: dict) -> list[dict]:
    ifc_class = asset_data.get("ifc_class")
    if ifc_class not in SERVICEABLE_IFC_CLASSES:
        return []

    checks = [
        ("manufacturer", "MISSING_MANUFACTURER", "Serviceable asset is missing manufacturer."),
        ("model", "MISSING_MODEL", "Serviceable asset is missing model."),
        ("serial_number", "MISSING_SERIAL_NUMBER", "Serviceable asset is missing serial number."),
    ]

    return [
        _issue(code, field, message)
        for field, code, message in checks
        if _is_blank(_field_value(asset_data, field))
    ]


def _check_status(asset_data: dict) -> list[dict]:
    status = _field_value(asset_data, "status")
    if _is_blank(status) or _is_placeholder(status):
        return []

    if not isinstance(status, str):
        return [
            _issue(
                "INVALID_STATUS",
                "status",
                "Asset status must be a string enum value.",
            )
        ]

    normalized = status.strip().lower().replace(" ", "_").replace("-", "_")
    if normalized not in DIGITAL_TWIN_STATUS_VALUES:
        return [
            _issue(
                "INVALID_STATUS",
                "status",
                "Asset status is not in the approved Digital Twin status values.",
            )
        ]

    return []


def validate_asset_data(asset_data: dict) -> list[dict]:
    issues: list[dict] = []

    issues.extend(_check_required_fields(asset_data))
    issues.extend(_check_placeholder_values(asset_data))
    issues.extend(_check_operational_name(asset_data))
    issues.extend(_check_asset_code_source(asset_data))
    issues.extend(_check_system(asset_data))
    issues.extend(_check_maintenance_fields(asset_data))
    issues.extend(_check_status(asset_data))

    return issues
