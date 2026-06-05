from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from src.db.session import get_db
from src.ifc.file_validator import IfcFileValidationError
from src.integrations.cloudflare_r2 import CloudflareR2ConfigError, get_cloudflare_r2_client
from src.models.asset import Asset
from src.models.ifc_element import IfcElement
from src.models.ifc_file import IfcFile
from src.models.enums import IfcFileStatus
from src.schemas.ifc_element import IfcElementDetailResponse, IfcElementListResponse
from src.schemas.ifc_file import IfcFileDeleteResponse, IfcFileListResponse, IfcFileResponse
from src.schemas.ifc_import import IfcImportQueuedResponse
from src.schemas.ifc_viewer_model import IfcViewerModelResponse
from src.services.ifc_import_service import IfcImportService
from src.tasks.ifc_import_tasks import process_uploaded_ifc_file


router = APIRouter(prefix="/ifc", tags=["ifc"])


def _ensure_ifc_file(db: Session, file_id: int) -> IfcFile:
    ifc_file = db.get(IfcFile, file_id)
    if ifc_file is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "IFC_FILE_NOT_FOUND", "message": "IFC file was not found."},
        )
    return ifc_file


def _asset_summary(asset: Asset | None) -> dict | None:
    if asset is None:
        return None

    return {
        "id": asset.id,
        "asset_code": asset.asset_code,
        "asset_type": asset.asset_type,
        "system_name": asset.system_name,
        "manufacturer": asset.manufacturer,
        "model": asset.model,
        "serial_number": asset.serial_number,
        "status": asset.status,
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
        "asset": _asset_summary(element.asset),
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
        "schema_name": ifc_file.schema_name,
        "total_elements": ifc_file.total_elements,
        "total_assets": ifc_file.total_assets,
        "total_issues": ifc_file.total_issues,
        "error_message": ifc_file.error_message,
        "viewer_model_status": ifc_file.viewer_model_status,
        "viewer_model_format": ifc_file.viewer_model_format,
        "viewer_model_size": ifc_file.viewer_model_size,
        "viewer_model_error": ifc_file.viewer_model_error,
        "created_at": ifc_file.created_at,
        "updated_at": ifc_file.updated_at,
    }


@router.post("/import", response_model=IfcImportQueuedResponse)
def import_ifc_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    service = IfcImportService(db)

    try:
        ifc_file = service.upload_file_for_background(file)
        task = process_uploaded_ifc_file.delay(ifc_file.id)
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

    return {
        "file_id": ifc_file.id,
        "filename": ifc_file.original_filename,
        "status": ifc_file.status,
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


@router.delete("/files/{file_id}", response_model=IfcFileDeleteResponse)
def delete_ifc_file(file_id: int, db: Session = Depends(get_db)):
    ifc_file = _ensure_ifc_file(db, file_id)
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
