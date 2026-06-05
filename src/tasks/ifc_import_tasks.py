from pathlib import Path
from uuid import uuid4

from src.core.celery_app import celery_app
from src.core.config import settings
from src.db.session import get_session_factory
from src.integrations.cloudflare_r2 import get_cloudflare_r2_client
from src.models.ifc_file import IfcFile
from src.services.ifc_import_service import IfcImportService


@celery_app.task(name="ifc.process_uploaded_file")
def process_uploaded_ifc_file(ifc_file_id: int) -> dict:
    db = get_session_factory()()
    tmp_path: Path | None = None

    try:
        ifc_file = db.get(IfcFile, ifc_file_id)
        if ifc_file is None:
            return {"status": "not_found", "file_id": ifc_file_id}

        tmp_dir = Path(settings.tmp_ifc_dir)
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_dir / f"worker-{uuid4().hex}-{Path(ifc_file.original_filename).name}"

        storage = get_cloudflare_r2_client()
        storage.download_file(ifc_file.storage_key, tmp_path)

        service = IfcImportService(db, storage=storage)
        service.process_existing_file(ifc_file, tmp_path)
        db.commit()
        db.refresh(ifc_file)

        return {
            "status": str(ifc_file.status),
            "file_id": ifc_file.id,
            "total_elements": ifc_file.total_elements,
            "total_assets": ifc_file.total_assets,
            "total_issues": ifc_file.total_issues,
            "viewer_model_status": ifc_file.viewer_model_status,
            "viewer_model_key": ifc_file.viewer_model_key,
        }
    except Exception as exc:
        db.rollback()
        ifc_file = db.get(IfcFile, ifc_file_id)
        if ifc_file is not None:
            service = IfcImportService(db)
            service.mark_failed(ifc_file, exc)
            db.commit()

        raise
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        db.close()
