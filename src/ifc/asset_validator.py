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
    return (
        normalized in PLACEHOLDER_VALUES
        or "placeholder" in normalized
        or normalized.startswith("to check")
    )


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
        "asset_tag",
        "description",
        "equipment_location",
        "equipment_type",
        "functional_location",
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
            "Asset code is using IFC GlobalId; Digital Twin handover requires a stable asset_id/asset code.",
        )
    ]


def _check_system(asset_data: dict) -> list[dict]:
    if _is_blank(_field_value(asset_data, "system_name")):
        ifc_class = asset_data.get("ifc_class")
        severity = (
            ValidationSeverity.ERROR
            if ifc_class in SYSTEM_REQUIRED_IFC_CLASSES
            else ValidationSeverity.WARNING
        )
        return [
            _issue(
                "MISSING_SYSTEM",
                "system_name",
                "Digital Twin asset is missing system name.",
                severity,
            )
        ]

    return []


def _check_handover_identifiers(asset_data: dict) -> list[dict]:
    issues = []
    asset_code = _field_value(asset_data, "asset_code")
    global_id = _field_value(asset_data, "global_id")

    if isinstance(asset_code, str) and isinstance(global_id, str):
        if asset_code.strip() == global_id.strip():
            issues.append(
                _issue(
                    "ASSET_CODE_EQUALS_IFC_GUID",
                    "asset_code",
                    "Asset ID should not be identical to IFC GlobalId in the handover package.",
                )
            )

    if not _is_blank(global_id) and not isinstance(global_id, str):
        issues.append(
            _issue(
                "INVALID_GLOBAL_ID",
                "global_id",
                "IFC GlobalId must be a text identifier.",
                ValidationSeverity.ERROR,
            )
        )

    return issues


def _check_handover_review_placeholders(asset_data: dict) -> list[dict]:
    issues = []
    properties = asset_data.get("properties")
    if not isinstance(properties, Mapping):
        return issues

    for field, value in properties.items():
        if _is_placeholder(value):
            issues.append(
                _issue(
                    "HANDOVER_PLACEHOLDER_VALUE",
                    str(field),
                    "Digital Twin handover field contains placeholder/review value.",
                )
            )

    return issues


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
    issues.extend(_check_handover_identifiers(asset_data))
    issues.extend(_check_asset_code_source(asset_data))
    issues.extend(_check_system(asset_data))
    issues.extend(_check_maintenance_fields(asset_data))
    issues.extend(_check_status(asset_data))
    issues.extend(_check_handover_review_placeholders(asset_data))

    return issues
