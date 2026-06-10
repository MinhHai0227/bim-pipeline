from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from botocore.exceptions import BotoCoreError, ClientError
from celery import chain

from src.core.celery_app import celery_app
from src.core.config import settings
from src.db.session import get_session_factory
from src.integrations.autodesk import AutodeskAPIError
from src.integrations.cloudflare_r2 import get_cloudflare_r2_client
from src.integrations.fragment_worker import FragmentWorkerError
from src.models.enums import IfcFileStatus
from src.models.ifc_file import IfcFile
from src.services.ifc_import_service import IfcImportService


RETRYABLE_EXCEPTIONS = (
    AutodeskAPIError,
    BotoCoreError,
    ClientError,
    FragmentWorkerError,
    OSError,
    TimeoutError,
)

NORMALIZE_TIME_LIMIT_SECONDS = settings.autodesk_model_derivative_timeout_seconds + 600
EXTRACT_TIME_LIMIT_SECONDS = 60 * 60
VIEWER_TIME_LIMIT_SECONDS = settings.fragment_worker_timeout_seconds + 300
FINALIZE_TIME_LIMIT_SECONDS = 5 * 60


EXTRACTED_STAGES = {
    "extracted",
    "viewer_converting",
    "viewer_converting_retrying",
    "viewer_ready",
    "viewer_failed",
    "viewer_skipped",
    "processed",
}


def enqueue_ifc_import_pipeline(ifc_file_id: int):
    return chain(
        normalize_uploaded_model.s(ifc_file_id),
        extract_uploaded_ifc.s(),
        convert_uploaded_viewer_model.s(),
        finalize_uploaded_ifc.s(),
    ).apply_async()


def _tmp_path_for(ifc_file: IfcFile, prefix: str, suffix: str | None = None) -> Path:
    tmp_dir = Path(settings.tmp_ifc_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(ifc_file.original_filename).name
    if suffix is not None:
        filename = f"{Path(filename).stem}{suffix}"

    return tmp_dir / f"{prefix}-{uuid4().hex}-{filename}"


def _retry_countdown(retries: int) -> int:
    return min(30 * (2**retries), 300)


def _is_retryable(exc: Exception) -> bool:
    return isinstance(exc, RETRYABLE_EXCEPTIONS)


def _mark_stage_retrying(task, db, ifc_file_id: int, exc: Exception, stage: str) -> None:
    ifc_file = db.get(IfcFile, ifc_file_id)
    if ifc_file is None:
        return

    service = IfcImportService(db)
    retry_number = task.request.retries + 1
    service.set_pipeline_stage(
        ifc_file,
        stage=f"{stage}_retrying",
        progress=ifc_file.pipeline_progress,
        message=f"{stage} failed; retry {retry_number}/{task.max_retries}: {exc}",
        status=IfcFileStatus.PROCESSING,
    )
    db.commit()


def _mark_failed(db, ifc_file_id: int, exc: Exception) -> None:
    ifc_file = db.get(IfcFile, ifc_file_id)
    if ifc_file is None:
        return

    IfcImportService(db).mark_failed(ifc_file, exc)
    db.commit()


def _retry_or_fail_pipeline(task, db, ifc_file_id: int, exc: Exception, stage: str) -> None:
    db.rollback()
    if _is_retryable(exc) and task.request.retries < task.max_retries:
        _mark_stage_retrying(task, db, ifc_file_id, exc, stage)
        raise task.retry(exc=exc, countdown=_retry_countdown(task.request.retries))

    _mark_failed(db, ifc_file_id, exc)
    raise exc


def _mark_viewer_failed(db, ifc_file_id: int, exc: Exception) -> None:
    ifc_file = db.get(IfcFile, ifc_file_id)
    if ifc_file is None:
        return

    ifc_file.viewer_model_status = "failed"
    ifc_file.viewer_model_error = str(exc)
    IfcImportService(db).set_pipeline_stage(
        ifc_file,
        stage="viewer_failed",
        progress=95,
        message=str(exc),
        status=IfcFileStatus.PROCESSING,
    )
    db.commit()


@celery_app.task(name="ifc.process_uploaded_file")
def process_uploaded_ifc_file(ifc_file_id: int) -> dict:
    task = enqueue_ifc_import_pipeline(ifc_file_id)
    return {"status": "queued", "file_id": ifc_file_id, "celery_task_id": task.id}


@celery_app.task(
    bind=True,
    name="ifc.normalize_uploaded_model",
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=max(NORMALIZE_TIME_LIMIT_SECONDS - 60, 60),
    time_limit=NORMALIZE_TIME_LIMIT_SECONDS,
)
def normalize_uploaded_model(self, ifc_file_id: int) -> int:
    db = get_session_factory()()
    tmp_path: Path | None = None
    normalized_tmp_path: Path | None = None

    try:
        ifc_file = db.get(IfcFile, ifc_file_id)
        if ifc_file is None:
            return ifc_file_id
        if (
            ifc_file.normalization_status == "ready"
            and ifc_file.normalized_ifc_storage_key
        ):
            service = IfcImportService(db)
            service.set_pipeline_stage(
                ifc_file,
                stage="normalized",
                progress=max(ifc_file.pipeline_progress, 35),
                message="Normalized IFC is already ready.",
                status=IfcFileStatus.PROCESSING,
            )
            db.commit()
            return ifc_file_id

        storage = get_cloudflare_r2_client()
        service = IfcImportService(db, storage=storage)
        service.set_pipeline_stage(
            ifc_file,
            stage="normalizing",
            progress=10,
            message="Downloading uploaded model for normalization.",
            status=IfcFileStatus.PROCESSING,
        )
        db.commit()

        tmp_path = _tmp_path_for(ifc_file, "normalize")
        storage.download_file(ifc_file.storage_key, tmp_path)
        if (ifc_file.source_format or "").lower() == "rvt":
            service.set_pipeline_stage(
                ifc_file,
                stage="normalizing",
                progress=20,
                message="Exporting RVT model to IFC through Autodesk Model Derivative.",
                status=IfcFileStatus.PROCESSING,
            )
            db.commit()

        normalized_tmp_path = service.normalize_existing_file(ifc_file, tmp_path)
        db.commit()
        return ifc_file_id
    except Exception as exc:
        _retry_or_fail_pipeline(self, db, ifc_file_id, exc, "normalizing")
    finally:
        if normalized_tmp_path is not None and normalized_tmp_path != tmp_path:
            normalized_tmp_path.unlink(missing_ok=True)
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        db.close()


@celery_app.task(
    bind=True,
    name="ifc.extract_uploaded_ifc",
    max_retries=2,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=EXTRACT_TIME_LIMIT_SECONDS - 60,
    time_limit=EXTRACT_TIME_LIMIT_SECONDS,
)
def extract_uploaded_ifc(self, ifc_file_id: int) -> int:
    db = get_session_factory()()
    tmp_path: Path | None = None

    try:
        ifc_file = db.get(IfcFile, ifc_file_id)
        if ifc_file is None:
            return ifc_file_id
        if ifc_file.pipeline_stage in EXTRACTED_STAGES:
            return ifc_file_id
        if not ifc_file.normalized_ifc_storage_key:
            raise ValueError("Normalized IFC object is missing.")

        storage = get_cloudflare_r2_client()
        service = IfcImportService(db, storage=storage)
        service.set_pipeline_stage(
            ifc_file,
            stage="extracting",
            progress=38,
            message="Downloading normalized IFC for extraction.",
            status=IfcFileStatus.PROCESSING,
        )
        db.commit()

        tmp_path = _tmp_path_for(ifc_file, "extract", suffix=".ifc")
        storage.download_file(ifc_file.normalized_ifc_storage_key, tmp_path)
        service.extract_existing_ifc(ifc_file, tmp_path)
        db.commit()
        return ifc_file_id
    except Exception as exc:
        _retry_or_fail_pipeline(self, db, ifc_file_id, exc, "extracting")
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        db.close()


@celery_app.task(
    bind=True,
    name="ifc.convert_uploaded_viewer_model",
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=max(VIEWER_TIME_LIMIT_SECONDS - 60, 60),
    time_limit=VIEWER_TIME_LIMIT_SECONDS,
)
def convert_uploaded_viewer_model(self, ifc_file_id: int) -> int:
    db = get_session_factory()()
    tmp_path: Path | None = None

    try:
        ifc_file = db.get(IfcFile, ifc_file_id)
        if ifc_file is None:
            return ifc_file_id
        if ifc_file.viewer_model_status in {"ready", "skipped"}:
            return ifc_file_id
        if not ifc_file.normalized_ifc_storage_key:
            raise ValueError("Normalized IFC object is missing.")

        storage = get_cloudflare_r2_client()
        service = IfcImportService(db, storage=storage)
        service.set_pipeline_stage(
            ifc_file,
            stage="viewer_converting",
            progress=78,
            message="Downloading normalized IFC for viewer conversion.",
            status=IfcFileStatus.PROCESSING,
        )
        db.commit()

        tmp_path = _tmp_path_for(ifc_file, "viewer", suffix=".ifc")
        storage.download_file(ifc_file.normalized_ifc_storage_key, tmp_path)
        service.convert_existing_viewer_model(ifc_file, tmp_path, suppress_errors=False)
        db.commit()
        return ifc_file_id
    except Exception as exc:
        db.rollback()
        if isinstance(exc, ValueError):
            _mark_failed(db, ifc_file_id, exc)
            raise exc

        if _is_retryable(exc) and self.request.retries < self.max_retries:
            _mark_stage_retrying(self, db, ifc_file_id, exc, "viewer_converting")
            raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries))

        _mark_viewer_failed(db, ifc_file_id, exc)
        return ifc_file_id
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        db.close()


@celery_app.task(
    bind=True,
    name="ifc.finalize_uploaded_ifc",
    max_retries=1,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=FINALIZE_TIME_LIMIT_SECONDS - 30,
    time_limit=FINALIZE_TIME_LIMIT_SECONDS,
)
def finalize_uploaded_ifc(self, ifc_file_id: int) -> dict:
    db = get_session_factory()()

    try:
        ifc_file = db.get(IfcFile, ifc_file_id)
        if ifc_file is None:
            return {"status": "not_found", "file_id": ifc_file_id}
        if ifc_file.status == IfcFileStatus.FAILED:
            return {"status": str(ifc_file.status), "file_id": ifc_file.id}
        if ifc_file.status == IfcFileStatus.PROCESSED:
            return {
                "status": str(ifc_file.status),
                "file_id": ifc_file.id,
                "pipeline_stage": ifc_file.pipeline_stage,
                "pipeline_progress": ifc_file.pipeline_progress,
            }

        IfcImportService(db).finalize_processed(ifc_file)
        db.commit()
        db.refresh(ifc_file)

        return {
            "status": str(ifc_file.status),
            "file_id": ifc_file.id,
            "source_format": ifc_file.source_format,
            "normalization_status": ifc_file.normalization_status,
            "normalized_ifc_storage_key": ifc_file.normalized_ifc_storage_key,
            "total_elements": ifc_file.total_elements,
            "total_assets": ifc_file.total_assets,
            "total_issues": ifc_file.total_issues,
            "viewer_model_status": ifc_file.viewer_model_status,
            "viewer_model_key": ifc_file.viewer_model_key,
            "pipeline_stage": ifc_file.pipeline_stage,
            "pipeline_progress": ifc_file.pipeline_progress,
        }
    except Exception as exc:
        _retry_or_fail_pipeline(self, db, ifc_file_id, exc, "finalizing")
    finally:
        db.close()
