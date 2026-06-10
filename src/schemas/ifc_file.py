from datetime import datetime

from pydantic import BaseModel

from src.models.enums import IfcFileStatus


class IfcFileResponse(BaseModel):
    id: int
    filename: str
    status: IfcFileStatus
    storage_key: str
    bucket_name: str
    content_type: str | None
    file_size: int | None
    source_format: str
    normalized_ifc_storage_key: str | None
    normalized_ifc_filename: str | None
    normalized_ifc_size: int | None
    normalization_status: str | None
    normalization_error: str | None
    autodesk_activity_id: str | None
    autodesk_workitem_id: str | None
    schema_name: str | None
    total_elements: int
    total_assets: int
    total_issues: int
    error_message: str | None
    viewer_model_status: str | None
    viewer_model_format: str | None
    viewer_model_size: int | None
    viewer_model_error: str | None
    pipeline_stage: str | None
    pipeline_progress: int
    pipeline_message: str | None
    created_at: datetime
    updated_at: datetime


class IfcFileListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[IfcFileResponse]


class IfcFileDeleteResponse(BaseModel):
    id: int
    filename: str
    deleted: bool
    deleted_storage_keys: list[str]
