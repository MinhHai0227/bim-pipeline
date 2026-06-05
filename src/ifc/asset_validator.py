from src.models.enums import ValidationSeverity, ValidationStage


def validate_asset_data(asset_data: dict) -> list[dict]:
    issues: list[dict] = []

    checks = [
        ("global_id", ValidationSeverity.ERROR, "MISSING_GLOBAL_ID", "Asset is missing GlobalId."),
        ("name", ValidationSeverity.WARNING, "MISSING_NAME", "Asset is missing Name."),
        ("asset_code", ValidationSeverity.WARNING, "MISSING_ASSET_CODE", "Asset is missing asset code."),
        ("floor", ValidationSeverity.WARNING, "MISSING_FLOOR", "Asset is missing floor."),
        ("room", ValidationSeverity.WARNING, "MISSING_ROOM", "Asset is missing room."),
    ]

    for field, severity, code, message in checks:
        value = asset_data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            issues.append(
                {
                    "stage": ValidationStage.ASSET_VALIDATION,
                    "severity": severity,
                    "code": code,
                    "field": field,
                    "message": message,
                }
            )

    return issues
