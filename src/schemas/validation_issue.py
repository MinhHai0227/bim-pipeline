from datetime import datetime

from pydantic import BaseModel

from src.models.enums import ValidationSeverity, ValidationStage


class ValidationIssueResponse(BaseModel):
    id: int
    ifc_file_id: int
    asset_id: int | None
    ifc_element_id: int | None
    global_id: str | None
    ifc_class: str | None
    object_name: str | None
    stage: ValidationStage
    severity: ValidationSeverity
    code: str
    field: str | None
    message: str
    created_at: datetime


class ValidationIssueListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ValidationIssueResponse]


class ValidationSummaryResponse(BaseModel):
    file_id: int
    total_issues: int
    by_severity: dict[str, int]
    by_stage: dict[str, int]
    by_code: dict[str, int]
