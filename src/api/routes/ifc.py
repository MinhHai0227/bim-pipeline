from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from src.db.session import get_db
from src.ifc.file_validator import IfcFileValidationError
from src.integrations.autodesk import AutodeskConfigError
from src.integrations.cloudflare_r2 import CloudflareR2ConfigError, get_cloudflare_r2_client
from src.models.asset import Asset
from src.models.enums import IfcFileStatus, ValidationSeverity, ValidationStage
from src.models.ifc_element import IfcElement
from src.models.ifc_file import IfcFile
from src.models.validation_issue import ValidationIssue
from src.schemas.digital_twin_asset import DigitalTwinAssetListResponse
from src.schemas.ifc_element import IfcElementDetailResponse, IfcElementListResponse
from src.schemas.ifc_file import IfcFileDeleteResponse, IfcFileListResponse, IfcFileResponse
from src.schemas.ifc_import import IfcImportQueuedResponse
from src.schemas.ifc_viewer_model import IfcViewerModelResponse
from src.schemas.validation_issue import ValidationIssueListResponse, ValidationSummaryResponse
from src.services.ifc_import_service import IfcImportService
from src.tasks.ifc_import_tasks import enqueue_ifc_import_pipeline, enqueue_ifc_reprocess_pipeline


router = APIRouter(prefix="/ifc", tags=["ifc"])


def _ensure_ifc_file(db: Session, file_id: int) -> IfcFile:
    ifc_file = db.get(IfcFile, file_id)
    if ifc_file is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "IFC_FILE_NOT_FOUND", "message": "IFC file was not found."},
        )
    return ifc_file


def _element_asset_response(asset: Asset | None) -> dict | None:
    if asset is None:
        return None

    return {
        "id": asset.id,
        "ifc_file_id": asset.ifc_file_id,
        "ifc_element_id": asset.ifc_element_id,
        "asset_code": asset.asset_code,
        "global_id": asset.global_id,
        "name": asset.name,
        "tag": asset.tag,
        "ifc_class": asset.ifc_class,
        "asset_type": asset.asset_type,
        "system_name": asset.system_name,
        "floor": asset.floor,
        "room": asset.room,
        "manufacturer": asset.manufacturer,
        "model": asset.model,
        "serial_number": asset.serial_number,
        "status": asset.status,
        "material": asset.material,
        "cleaning_log": asset.cleaning_log,
    }


def _element_list_item(element: IfcElement) -> dict:
    return {
        "id": element.id,
        "ifc_file_id": element.ifc_file_id,
        "express_id": element.express_id,
        "global_id": element.global_id,
        "ifc_class": element.ifc_class,
        "name": element.name,
        "tag": element.tag,
        "is_asset": element.asset is not None,
    }


def _element_detail(element: IfcElement) -> dict:
    return {
        **_element_list_item(element),
        "floor": element.floor,
        "room": element.room,
        "material": element.material,
        "properties": element.properties,
        "quantities": element.quantities,
        "raw_properties": element.raw_properties,
        "asset": _element_asset_response(element.asset),
    }


def _file_response(ifc_file: IfcFile) -> dict:
    return {
        "id": ifc_file.id,
        "filename": ifc_file.original_filename,
        "status": ifc_file.status,
        "storage_key": ifc_file.storage_key,
        "bucket_name": ifc_file.bucket_name,
        "content_type": ifc_file.content_type,
        "file_size": ifc_file.file_size,
        "source_format": ifc_file.source_format,
        "normalized_ifc_storage_key": ifc_file.normalized_ifc_storage_key,
        "normalized_ifc_filename": ifc_file.normalized_ifc_filename,
        "normalized_ifc_size": ifc_file.normalized_ifc_size,
        "normalization_status": ifc_file.normalization_status,
        "normalization_error": ifc_file.normalization_error,
        "autodesk_activity_id": ifc_file.autodesk_activity_id,
        "autodesk_workitem_id": ifc_file.autodesk_workitem_id,
        "schema_name": ifc_file.schema_name,
        "total_elements": ifc_file.total_elements,
        "total_assets": ifc_file.total_assets,
        "total_issues": ifc_file.total_issues,
        "error_message": ifc_file.error_message,
        "viewer_model_status": ifc_file.viewer_model_status,
        "viewer_model_format": ifc_file.viewer_model_format,
        "viewer_model_size": ifc_file.viewer_model_size,
        "viewer_model_error": ifc_file.viewer_model_error,
        "pipeline_stage": ifc_file.pipeline_stage,
        "pipeline_progress": ifc_file.pipeline_progress,
        "pipeline_message": ifc_file.pipeline_message,
        "created_at": ifc_file.created_at,
        "updated_at": ifc_file.updated_at,
    }


def _validation_issue_response(issue: ValidationIssue) -> dict:
    return {
        "id": issue.id,
        "ifc_file_id": issue.ifc_file_id,
        "asset_id": issue.asset_id,
        "ifc_element_id": issue.ifc_element_id,
        "global_id": issue.global_id,
        "ifc_class": issue.ifc_class,
        "object_name": issue.object_name,
        "stage": issue.stage,
        "severity": issue.severity,
        "code": issue.code,
        "field": issue.field,
        "message": issue.message,
        "created_at": issue.created_at,
    }


def _asset_location(asset: Asset) -> str | None:
    parts = [part for part in (asset.floor, asset.room) if part]
    return " > ".join(parts) if parts else None


def _digital_twin_asset_response(asset: Asset) -> dict:
    return {
        "id": asset.id,
        "ifc_file_id": asset.ifc_file_id,
        "ifc_element_id": asset.ifc_element_id,
        "global_id": asset.global_id,
        "asset_id": asset.asset_code,
        "asset_name": asset.name,
        "asset_type": asset.asset_type,
        "ifc_class": asset.ifc_class,
        "system": asset.system_name,
        "location": _asset_location(asset),
        "floor": asset.floor,
        "room_zone": asset.room,
        "manufacturer": asset.manufacturer,
        "model": asset.model,
        "serial_number": asset.serial_number,
        "status": asset.status,
        "cleaning_log": asset.cleaning_log,
    }


def _enum_key(value) -> str:
    return getattr(value, "value", str(value))


@router.post("/import", response_model=IfcImportQueuedResponse)
def import_ifc_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    service = IfcImportService(db)

    try:
        ifc_file = service.upload_file_for_background(file)
        task = enqueue_ifc_import_pipeline(ifc_file.id)
    except IfcFileValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "stage": "file_validation",
                "code": exc.code,
                "message": exc.message,
            },
        ) from exc
    except CloudflareR2ConfigError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "CLOUDFLARE_R2_NOT_CONFIGURED", "message": str(exc)},
        ) from exc
    except AutodeskConfigError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "AUTODESK_NOT_CONFIGURED", "message": str(exc)},
        ) from exc

    return {
        "file_id": ifc_file.id,
        "filename": ifc_file.original_filename,
        "status": ifc_file.status,
        "source_format": ifc_file.source_format,
        "normalization_status": ifc_file.normalization_status,
        "pipeline_stage": ifc_file.pipeline_stage,
        "pipeline_progress": ifc_file.pipeline_progress,
        "pipeline_message": ifc_file.pipeline_message,
        "storage_key": ifc_file.storage_key,
        "bucket_name": ifc_file.bucket_name,
        "celery_task_id": task.id,
    }


@router.get("/files", response_model=IfcFileListResponse)
def list_ifc_files(
    status: IfcFileStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    filters = []
    if status is not None:
        filters.append(IfcFile.status == status)

    total = db.scalar(select(func.count()).select_from(IfcFile).where(*filters)) or 0
    files = db.scalars(
        select(IfcFile)
        .where(*filters)
        .order_by(IfcFile.created_at.desc(), IfcFile.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_file_response(ifc_file) for ifc_file in files],
    }


@router.get("/files/{file_id}", response_model=IfcFileResponse)
def get_ifc_file(file_id: int, db: Session = Depends(get_db)):
    return _file_response(_ensure_ifc_file(db, file_id))


@router.post("/files/{file_id}/reprocess", response_model=IfcImportQueuedResponse)
def reprocess_ifc_file(file_id: int, db: Session = Depends(get_db)):
    ifc_file = _ensure_ifc_file(db, file_id)
    if ifc_file.status == IfcFileStatus.PROCESSING:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "IFC_FILE_PROCESSING",
                "message": "IFC file is still processing and cannot be reprocessed.",
                "pipeline_stage": ifc_file.pipeline_stage,
                "pipeline_progress": ifc_file.pipeline_progress,
            },
        )

    ifc_file.error_message = None
    ifc_file.viewer_model_status = "pending"
    ifc_file.viewer_model_error = None
    IfcImportService(db).set_pipeline_stage(
        ifc_file,
        stage="reprocess_queued",
        progress=0,
        message="Reprocessing model with current extraction and validation rules.",
        status=IfcFileStatus.PROCESSING,
    )
    db.commit()
    db.refresh(ifc_file)

    task = enqueue_ifc_reprocess_pipeline(ifc_file.id)

    return {
        "file_id": ifc_file.id,
        "filename": ifc_file.original_filename,
        "status": ifc_file.status,
        "source_format": ifc_file.source_format,
        "normalization_status": ifc_file.normalization_status,
        "pipeline_stage": ifc_file.pipeline_stage,
        "pipeline_progress": ifc_file.pipeline_progress,
        "pipeline_message": ifc_file.pipeline_message,
        "storage_key": ifc_file.storage_key,
        "bucket_name": ifc_file.bucket_name,
        "celery_task_id": task.id,
    }


@router.get("/files/{file_id}/issues", response_model=ValidationIssueListResponse)
def list_validation_issues(
    file_id: int,
    severity: ValidationSeverity | None = Query(default=None),
    stage: ValidationStage | None = Query(default=None),
    code: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    _ensure_ifc_file(db, file_id)

    filters = [ValidationIssue.ifc_file_id == file_id]
    if severity is not None:
        filters.append(ValidationIssue.severity == severity)
    if stage is not None:
        filters.append(ValidationIssue.stage == stage)
    if code:
        filters.append(ValidationIssue.code == code)

    total = db.scalar(select(func.count()).select_from(ValidationIssue).where(*filters)) or 0
    issues = db.scalars(
        select(ValidationIssue)
        .where(*filters)
        .order_by(ValidationIssue.created_at.desc(), ValidationIssue.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_validation_issue_response(issue) for issue in issues],
    }


@router.get("/files/{file_id}/validation-summary", response_model=ValidationSummaryResponse)
def get_validation_summary(file_id: int, db: Session = Depends(get_db)):
    _ensure_ifc_file(db, file_id)

    total_issues = (
        db.scalar(
            select(func.count())
            .select_from(ValidationIssue)
            .where(ValidationIssue.ifc_file_id == file_id)
        )
        or 0
    )

    severity_rows = db.execute(
        select(ValidationIssue.severity, func.count())
        .where(ValidationIssue.ifc_file_id == file_id)
        .group_by(ValidationIssue.severity)
    ).all()
    stage_rows = db.execute(
        select(ValidationIssue.stage, func.count())
        .where(ValidationIssue.ifc_file_id == file_id)
        .group_by(ValidationIssue.stage)
    ).all()
    code_rows = db.execute(
        select(ValidationIssue.code, func.count())
        .where(ValidationIssue.ifc_file_id == file_id)
        .group_by(ValidationIssue.code)
        .order_by(func.count().desc(), ValidationIssue.code)
    ).all()

    return {
        "file_id": file_id,
        "total_issues": total_issues,
        "by_severity": {_enum_key(value): count for value, count in severity_rows},
        "by_stage": {_enum_key(value): count for value, count in stage_rows},
        "by_code": {str(value): count for value, count in code_rows},
    }


@router.get("/files/{file_id}/digital-twin-assets", response_model=DigitalTwinAssetListResponse)
def list_digital_twin_assets(
    file_id: int,
    q: str | None = Query(default=None),
    system: str | None = Query(default=None),
    asset_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    _ensure_ifc_file(db, file_id)

    filters = [Asset.ifc_file_id == file_id]
    if system:
        filters.append(Asset.system_name == system)
    if asset_type:
        filters.append(Asset.asset_type == asset_type)
    if q:
        search = f"%{q}%"
        filters.append(
            or_(
                Asset.asset_code.ilike(search),
                Asset.global_id.ilike(search),
                Asset.ifc_class.ilike(search),
                Asset.name.ilike(search),
                Asset.tag.ilike(search),
            )
        )

    total = db.scalar(select(func.count()).select_from(Asset).where(*filters)) or 0
    assets = db.scalars(
        select(Asset)
        .where(*filters)
        .order_by(Asset.id)
        .offset(offset)
        .limit(limit)
    ).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_digital_twin_asset_response(asset) for asset in assets],
    }


@router.delete("/files/{file_id}", response_model=IfcFileDeleteResponse)
def delete_ifc_file(file_id: int, db: Session = Depends(get_db)):
    ifc_file = _ensure_ifc_file(db, file_id)
    if ifc_file.status == IfcFileStatus.PROCESSING:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "IFC_FILE_PROCESSING",
                "message": "IFC file is still processing and cannot be deleted.",
                "pipeline_stage": ifc_file.pipeline_stage,
                "pipeline_progress": ifc_file.pipeline_progress,
            },
        )

    deleted_file_id = ifc_file.id
    deleted_filename = ifc_file.original_filename
    service = IfcImportService(db)

    try:
        deleted_storage_keys = service.delete_ifc_file(ifc_file)
    except CloudflareR2ConfigError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "CLOUDFLARE_R2_NOT_CONFIGURED", "message": str(exc)},
        ) from exc
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "R2_DELETE_FAILED", "message": str(exc)},
        ) from exc

    return {
        "id": deleted_file_id,
        "filename": deleted_filename,
        "deleted": True,
        "deleted_storage_keys": deleted_storage_keys,
    }


@router.get("/files/{file_id}/viewer-model", response_model=IfcViewerModelResponse)
def get_ifc_viewer_model(
    file_id: int,
    expires_in: int = Query(default=3600, ge=60, le=86400),
    db: Session = Depends(get_db),
):
    ifc_file = _ensure_ifc_file(db, file_id)
    url = None

    if ifc_file.viewer_model_status == "ready" and ifc_file.viewer_model_key:
        try:
            url = get_cloudflare_r2_client().presigned_get_url(
                ifc_file.viewer_model_key,
                expires_in=expires_in,
            )
        except CloudflareR2ConfigError as exc:
            raise HTTPException(
                status_code=500,
                detail={"code": "CLOUDFLARE_R2_NOT_CONFIGURED", "message": str(exc)},
            ) from exc

    return {
        "file_id": ifc_file.id,
        "status": ifc_file.viewer_model_status,
        "format": ifc_file.viewer_model_format,
        "storage_key": ifc_file.viewer_model_key,
        "size": ifc_file.viewer_model_size,
        "url": url,
        "error": ifc_file.viewer_model_error,
    }


@router.get("/files/{file_id}/viewer-model/download")
def download_ifc_viewer_model(
    file_id: int,
    db: Session = Depends(get_db),
):
    ifc_file = _ensure_ifc_file(db, file_id)

    if ifc_file.viewer_model_status != "ready" or not ifc_file.viewer_model_key:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "IFC_VIEWER_MODEL_NOT_READY",
                "message": "IFC viewer model is not ready.",
            },
        )

    try:
        storage = get_cloudflare_r2_client()
        response = storage.client().get_object(
            Bucket=storage.bucket_name,
            Key=ifc_file.viewer_model_key,
        )
    except CloudflareR2ConfigError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "CLOUDFLARE_R2_NOT_CONFIGURED", "message": str(exc)},
        ) from exc

    body = response["Body"]
    filename = f"{ifc_file.id}.frag"

    return StreamingResponse(
        body.iter_chunks(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, max-age=300",
        },
    )


@router.get("/files/{file_id}/elements", response_model=IfcElementListResponse)
def list_ifc_elements(
    file_id: int,
    ifc_class: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    _ensure_ifc_file(db, file_id)

    filters = [IfcElement.ifc_file_id == file_id]
    if ifc_class:
        filters.append(IfcElement.ifc_class == ifc_class)
    if q:
        search = f"%{q}%"
        filters.append(
            or_(
                IfcElement.global_id.ilike(search),
                IfcElement.ifc_class.ilike(search),
                IfcElement.name.ilike(search),
                IfcElement.tag.ilike(search),
            )
        )

    total = db.scalar(select(func.count()).select_from(IfcElement).where(*filters)) or 0
    elements = db.scalars(
        select(IfcElement)
        .options(selectinload(IfcElement.asset))
        .where(*filters)
        .order_by(IfcElement.id)
        .offset(offset)
        .limit(limit)
    ).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_element_list_item(element) for element in elements],
    }


@router.get(
    "/files/{file_id}/elements/by-global-id/{global_id}",
    response_model=IfcElementDetailResponse,
)
def get_ifc_element_by_global_id(
    file_id: int,
    global_id: str,
    db: Session = Depends(get_db),
):
    _ensure_ifc_file(db, file_id)

    element = db.scalars(
        select(IfcElement)
        .options(selectinload(IfcElement.asset))
        .where(
            IfcElement.ifc_file_id == file_id,
            IfcElement.global_id == global_id,
        )
    ).first()
    if element is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "IFC_ELEMENT_NOT_FOUND", "message": "IFC element was not found."},
        )

    return _element_detail(element)


@router.get(
    "/files/{file_id}/elements/by-express-id/{express_id}",
    response_model=IfcElementDetailResponse,
)
def get_ifc_element_by_express_id(
    file_id: int,
    express_id: int,
    db: Session = Depends(get_db),
):
    _ensure_ifc_file(db, file_id)

    element = db.scalars(
        select(IfcElement)
        .options(selectinload(IfcElement.asset))
        .where(
            IfcElement.ifc_file_id == file_id,
            IfcElement.express_id == express_id,
        )
    ).first()
    if element is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "IFC_ELEMENT_NOT_FOUND", "message": "IFC element was not found."},
        )

    return _element_detail(element)
