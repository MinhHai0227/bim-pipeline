from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import delete
from sqlalchemy.orm import Session

from src.core.config import settings
from src.ifc.asset_detector import is_operational_asset
from src.ifc.asset_cleaner import clean_asset_data
from src.ifc.asset_validator import validate_asset_data
from src.ifc.extractor import IFCExtractor
from src.ifc.file_validator import (
    IfcFileValidationError,
    validate_ifc_file_size,
    validate_ifc_filename,
)
from src.integrations.cloudflare_r2 import CloudflareR2Client, get_cloudflare_r2_client
from src.integrations.fragment_worker import FragmentWorkerClient
from src.models.asset import Asset
from src.models.enums import IfcFileStatus, ValidationSeverity, ValidationStage
from src.models.ifc_element import IfcElement
from src.models.ifc_file import IfcFile
from src.models.validation_issue import ValidationIssue


class IfcImportService:
    def __init__(
        self,
        db: Session,
        storage: CloudflareR2Client | None = None,
    ) -> None:
        self.db = db
        self.storage = storage or get_cloudflare_r2_client()

    @property
    def max_size_bytes(self) -> int:
        return settings.max_ifc_upload_size_mb * 1024 * 1024

    def upload_file_for_background(self, upload: UploadFile) -> IfcFile:
        safe_filename = validate_ifc_filename(upload.filename)
        tmp_path = self._save_upload_to_tmp(upload, safe_filename)

        try:
            storage_key = self.storage.build_key(f"{uuid4().hex}-{safe_filename}")
            with tmp_path.open("rb") as fileobj:
                self.storage.upload_fileobj(
                    fileobj=fileobj,
                    filename=safe_filename,
                    key=storage_key,
                    content_type=upload.content_type,
                )

            ifc_file = IfcFile(
                original_filename=safe_filename,
                storage_key=storage_key,
                bucket_name=self.storage.bucket_name,
                content_type=upload.content_type,
                file_size=tmp_path.stat().st_size,
                status=IfcFileStatus.UPLOADED,
                viewer_model_status="pending",
            )
            self.db.add(ifc_file)
            self.db.commit()
            self.db.refresh(ifc_file)
            return ifc_file
        except Exception:
            self.db.rollback()
            raise
        finally:
            tmp_path.unlink(missing_ok=True)

    def _save_upload_to_tmp(self, upload: UploadFile, safe_filename: str) -> Path:
        tmp_dir = Path(settings.tmp_ifc_dir)
        tmp_dir.mkdir(parents=True, exist_ok=True)

        tmp_path = tmp_dir / f"{uuid4().hex}-{safe_filename}"
        file_size = 0

        with tmp_path.open("wb") as destination:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break

                file_size += len(chunk)
                if file_size > self.max_size_bytes:
                    tmp_path.unlink(missing_ok=True)
                    raise IfcFileValidationError(
                        "FILE_TOO_LARGE",
                        f"Uploaded IFC file exceeds {settings.max_ifc_upload_size_mb}MB.",
                    )

                destination.write(chunk)

        try:
            validate_ifc_file_size(file_size, self.max_size_bytes)
        except IfcFileValidationError:
            tmp_path.unlink(missing_ok=True)
            raise

        return tmp_path

    def _process_ifc_file(self, ifc_file: IfcFile, tmp_path: Path) -> None:
        ifc_file.status = IfcFileStatus.PROCESSING
        ifc_file.error_message = None
        ifc_file.viewer_model_status = "pending"
        ifc_file.viewer_model_error = None
        self.db.add(ifc_file)
        self.db.flush()
        self._clear_previous_import_data(ifc_file.id)

        extractor = IFCExtractor(tmp_path)
        ifc_file.schema_name = extractor.schema_name

        total_elements = 0
        total_assets = 0
        total_issues = 0
        seen_global_ids: set[str] = set()
        seen_asset_codes: set[str] = set()

        for element in extractor.iter_products():
            total_elements += 1
            asset_data = extractor.extract_element(element)

            ifc_element = self._create_ifc_element(ifc_file.id, asset_data)
            self.db.add(ifc_element)
            self.db.flush()

            if not is_operational_asset(element, asset_data["raw_properties"]):
                continue

            self._normalize_asset_data(asset_data)
            cleaning_log = clean_asset_data(asset_data)
            issues = validate_asset_data(asset_data)

            asset = self._create_asset(ifc_file.id, ifc_element.id, asset_data, cleaning_log)
            self.db.add(asset)
            self.db.flush()
            total_assets += 1

            global_id = asset_data.get("global_id")
            if global_id:
                if global_id in seen_global_ids:
                    issues.append(
                        {
                            "stage": ValidationStage.ASSET_VALIDATION,
                            "severity": ValidationSeverity.ERROR,
                            "code": "DUPLICATE_GLOBAL_ID",
                            "field": "global_id",
                            "message": "Asset GlobalId appears more than once in this import.",
                        }
                    )
                seen_global_ids.add(global_id)

            asset_code = asset_data.get("asset_code")
            if asset_code:
                if asset_code in seen_asset_codes:
                    issues.append(
                        {
                            "stage": ValidationStage.ASSET_VALIDATION,
                            "severity": ValidationSeverity.ERROR,
                            "code": "DUPLICATE_ASSET_CODE",
                            "field": "asset_code",
                            "message": "Asset code appears more than once in this import.",
                        }
                    )
                seen_asset_codes.add(asset_code)

            total_issues += self._create_validation_issues(
                ifc_file.id,
                asset.id,
                ifc_element.id,
                asset_data,
                issues,
            )

        ifc_file.total_elements = total_elements
        ifc_file.total_assets = total_assets
        ifc_file.total_issues = total_issues
        ifc_file.status = IfcFileStatus.PROCESSED
        self._convert_and_upload_viewer_model(ifc_file, tmp_path)

    def process_existing_file(self, ifc_file: IfcFile, tmp_path: Path) -> None:
        self._process_ifc_file(ifc_file, tmp_path)

    def delete_ifc_file(self, ifc_file: IfcFile) -> list[str]:
        storage_keys = self._storage_keys_for_delete(ifc_file)

        try:
            for storage_key in storage_keys:
                self.storage.delete_object(storage_key)

            self._clear_previous_import_data(ifc_file.id)
            self.db.delete(ifc_file)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return storage_keys

    def _storage_keys_for_delete(self, ifc_file: IfcFile) -> list[str]:
        storage_keys = []
        for storage_key in (ifc_file.storage_key, ifc_file.viewer_model_key):
            if storage_key and storage_key not in storage_keys:
                storage_keys.append(storage_key)

        return storage_keys

    def _clear_previous_import_data(self, ifc_file_id: int) -> None:
        self.db.execute(delete(ValidationIssue).where(ValidationIssue.ifc_file_id == ifc_file_id))
        self.db.execute(delete(Asset).where(Asset.ifc_file_id == ifc_file_id))
        self.db.execute(delete(IfcElement).where(IfcElement.ifc_file_id == ifc_file_id))

    def _normalize_asset_data(self, asset_data: dict) -> None:
        properties = asset_data.get("properties") or {}
        tag = asset_data.get("tag")
        asset_code_sources = [
            ("asset_identifier", properties.get("asset_identifier")),
            ("tag", tag),
            ("reference", properties.get("reference")),
            ("global_id", asset_data.get("global_id")),
        ]

        for source, asset_code in asset_code_sources:
            if asset_code:
                asset_data["asset_code"] = str(asset_code)
                asset_data["asset_code_source"] = source
                return

        asset_data["asset_code"] = None
        asset_data["asset_code_source"] = None

    def _create_ifc_element(self, ifc_file_id: int, asset_data: dict) -> IfcElement:
        return IfcElement(
            ifc_file_id=ifc_file_id,
            express_id=asset_data.get("express_id"),
            global_id=asset_data.get("global_id"),
            ifc_class=asset_data.get("ifc_class"),
            name=asset_data.get("name"),
            tag=asset_data.get("tag"),
            floor=asset_data.get("floor"),
            room=asset_data.get("room"),
            material=asset_data.get("material"),
            properties=deepcopy(asset_data.get("properties") or {}),
            quantities=deepcopy(asset_data.get("quantities") or {}),
            raw_properties=deepcopy(asset_data.get("raw_properties") or {}),
        )

    def _create_asset(
        self,
        ifc_file_id: int,
        ifc_element_id: int,
        asset_data: dict,
        cleaning_log: list[dict],
    ) -> Asset:
        properties = asset_data.get("properties") or {}

        return Asset(
            ifc_file_id=ifc_file_id,
            ifc_element_id=ifc_element_id,
            asset_code=asset_data.get("asset_code"),
            global_id=asset_data.get("global_id"),
            name=asset_data.get("name"),
            tag=asset_data.get("tag"),
            ifc_class=asset_data.get("ifc_class"),
            asset_type=asset_data.get("asset_type") or asset_data.get("ifc_class"),
            system_name=properties.get("system_name"),
            floor=asset_data.get("floor"),
            room=asset_data.get("room"),
            manufacturer=properties.get("manufacturer"),
            model=properties.get("model"),
            serial_number=properties.get("serial_number"),
            status=properties.get("status"),
            material=asset_data.get("material"),
            cleaning_log=deepcopy(cleaning_log),
        )

    def _create_validation_issues(
        self,
        ifc_file_id: int,
        asset_id: int,
        ifc_element_id: int,
        asset_data: dict,
        issues: list[dict],
    ) -> int:
        for issue in issues:
            self.db.add(
                ValidationIssue(
                    ifc_file_id=ifc_file_id,
                    asset_id=asset_id,
                    ifc_element_id=ifc_element_id,
                    global_id=asset_data.get("global_id"),
                    ifc_class=asset_data.get("ifc_class"),
                    object_name=asset_data.get("name"),
                    stage=issue.get("stage", ValidationStage.ASSET_VALIDATION),
                    severity=issue["severity"],
                    code=issue["code"],
                    field=issue.get("field"),
                    message=issue["message"],
                )
            )

        return len(issues)

    def _convert_and_upload_viewer_model(self, ifc_file: IfcFile, tmp_path: Path) -> None:
        if not settings.fragment_worker_url:
            ifc_file.viewer_model_status = "skipped"
            ifc_file.viewer_model_error = "FRAGMENT_WORKER_URL is not configured."
            return

        frag_path = tmp_path.parent / f"{tmp_path.stem}-{uuid4().hex}.frag"
        ifc_file.viewer_model_status = "converting"
        ifc_file.viewer_model_format = "frag"
        ifc_file.viewer_model_key = None
        ifc_file.viewer_model_size = None
        ifc_file.viewer_model_error = None
        self.db.add(ifc_file)
        self.db.flush()

        try:
            FragmentWorkerClient().convert_ifc_to_frag(tmp_path, frag_path)
            viewer_model_key = self.storage.build_key(
                f"ifc-file-{ifc_file.id}-{uuid4().hex}.frag",
                prefix="viewer-models/fragments",
            )

            with frag_path.open("rb") as fileobj:
                self.storage.upload_fileobj(
                    fileobj=fileobj,
                    filename=frag_path.name,
                    key=viewer_model_key,
                    content_type="application/octet-stream",
                )

            ifc_file.viewer_model_key = viewer_model_key
            ifc_file.viewer_model_size = frag_path.stat().st_size
            ifc_file.viewer_model_status = "ready"
            ifc_file.viewer_model_error = None
        except Exception as exc:
            ifc_file.viewer_model_status = "failed"
            ifc_file.viewer_model_error = str(exc)
        finally:
            frag_path.unlink(missing_ok=True)

    def mark_failed(self, ifc_file: IfcFile, exc: Exception) -> None:
        ifc_file.status = IfcFileStatus.FAILED
        ifc_file.error_message = str(exc)
        ifc_file.total_issues = max(ifc_file.total_issues, 1)
        ifc_file.viewer_model_status = "failed"
        ifc_file.viewer_model_error = str(exc)

        self.db.add(ifc_file)
        self.db.add(
            ValidationIssue(
                ifc_file_id=ifc_file.id,
                stage=ValidationStage.IFC_PARSE,
                severity=ValidationSeverity.ERROR,
                code="IFC_IMPORT_FAILED",
                message=str(exc),
            )
        )
