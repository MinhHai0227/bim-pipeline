from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from src.core.config import settings


class AutodeskConfigError(RuntimeError):
    pass


class AutodeskAPIError(RuntimeError):
    pass


class AutodeskModelDerivativeError(AutodeskAPIError):
    pass


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


@dataclass
class AutodeskToken:
    access_token: str
    expires_at: datetime

    def is_valid(self) -> bool:
        return datetime.now(UTC) < self.expires_at


class AutodeskAuthClient:
    def __init__(self) -> None:
        self._token: AutodeskToken | None = None

    def _credentials(self) -> tuple[str, str]:
        client_id = _clean(settings.autodesk_client_id)
        client_secret = _clean(settings.autodesk_client_secret)
        if not client_id:
            raise AutodeskConfigError("AUTODESK_CLIENT_ID is required for RVT to IFC export.")
        if not client_secret:
            raise AutodeskConfigError("AUTODESK_CLIENT_SECRET is required for RVT to IFC export.")

        return client_id, client_secret

    def get_access_token(self) -> str:
        if self._token and self._token.is_valid():
            return self._token.access_token

        client_id, client_secret = self._credentials()
        basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode(
            "ascii"
        )
        payload = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "scope": settings.autodesk_scopes,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            settings.autodesk_token_url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Basic {basic_auth}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )

        response = self._open_json(request)
        access_token = response.get("access_token")
        if not access_token:
            raise AutodeskAPIError("Autodesk token response did not include access_token.")

        expires_in = int(response.get("expires_in") or 3599)
        expires_at = datetime.now(UTC) + timedelta(seconds=max(expires_in - 60, 1))
        self._token = AutodeskToken(access_token=access_token, expires_at=expires_at)
        return access_token

    def _open_json(self, request: urllib.request.Request) -> dict:
        try:
            with urllib.request.urlopen(
                request,
                timeout=settings.autodesk_http_timeout_seconds,
            ) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise AutodeskAPIError(f"Autodesk authentication failed: {detail}") from exc
        except urllib.error.URLError as exc:
            raise AutodeskAPIError(f"Autodesk authentication request failed: {exc.reason}") from exc

        if not body:
            return {}
        return json.loads(body)


class AutodeskModelDerivativeClient:
    SUCCESS_STATUSES = {"success"}
    RUNNING_STATUSES = {"pending", "inprogress"}
    FAILED_STATUSES = {"failed", "timeout"}

    def __init__(self, auth_client: AutodeskAuthClient | None = None) -> None:
        self.auth_client = auth_client or AutodeskAuthClient()

    @staticmethod
    def validate_rvt_to_ifc_settings() -> None:
        AutodeskAuthClient()._credentials()
        if not _clean(settings.autodesk_bucket_key):
            raise AutodeskConfigError("AUTODESK_BUCKET_KEY is required for RVT to IFC export.")

    def export_rvt_to_ifc(
        self,
        input_path: str | Path,
        output_path: str | Path,
        object_name: str,
    ) -> dict:
        self.validate_rvt_to_ifc_settings()
        bucket_key = self._bucket_key()

        self.ensure_bucket(bucket_key)
        object_info = self.upload_object(bucket_key, object_name, input_path)
        object_id = object_info.get("objectId")
        if not object_id:
            raise AutodeskAPIError("Autodesk OSS upload response did not include objectId.")

        urn = self._urn_from_object_id(object_id)
        self.start_ifc_job(urn)
        manifest = self.wait_for_manifest(urn)
        derivative_urn = self.find_ifc_derivative_urn(manifest)
        self.download_derivative(urn, derivative_urn, output_path)

        return {
            "bucket_key": bucket_key,
            "object_name": object_name,
            "object_id": object_id,
            "urn": urn,
            "derivative_urn": derivative_urn,
        }

    def _bucket_key(self) -> str:
        bucket_key = _clean(settings.autodesk_bucket_key)
        if not bucket_key:
            raise AutodeskConfigError("AUTODESK_BUCKET_KEY is required for RVT to IFC export.")
        return bucket_key

    def ensure_bucket(self, bucket_key: str) -> None:
        payload = {
            "bucketKey": bucket_key,
            "policyKey": settings.autodesk_bucket_policy_key,
        }
        try:
            self._request_json("POST", f"{self._oss_base_url()}/buckets", payload)
        except AutodeskAPIError as exc:
            if "409" not in str(exc) and "Bucket already exists" not in str(exc):
                raise

    def upload_object(self, bucket_key: str, object_name: str, input_path: str | Path) -> dict:
        safe_object_name = Path(object_name).name
        signed_upload = self.create_signed_upload(bucket_key, safe_object_name)
        urls = signed_upload.get("urls") or ([signed_upload["url"]] if signed_upload.get("url") else [])
        upload_key = signed_upload.get("uploadKey")

        if not urls:
            raise AutodeskAPIError(
                f"Autodesk signed upload response did not include upload URL: "
                f"{json.dumps(signed_upload, ensure_ascii=True)}"
            )
        if not upload_key:
            raise AutodeskAPIError(
                f"Autodesk signed upload response did not include uploadKey: "
                f"{json.dumps(signed_upload, ensure_ascii=True)}"
            )

        self.upload_to_signed_url(str(urls[0]), input_path)
        return self.complete_signed_upload(bucket_key, safe_object_name, str(upload_key))

    def create_signed_upload(self, bucket_key: str, object_name: str) -> dict:
        quoted_bucket = urllib.parse.quote(bucket_key, safe="")
        quoted_object = urllib.parse.quote(object_name, safe="")
        url = (
            f"{self._oss_base_url()}/buckets/{quoted_bucket}/objects/{quoted_object}"
            "/signeds3upload?parts=1"
        )

        return self._request_json("GET", url)

    def upload_to_signed_url(self, signed_url: str, input_path: str | Path) -> None:
        data = Path(input_path).read_bytes()
        request = urllib.request.Request(
            signed_url,
            data=data,
            method="PUT",
            headers={
                "Content-Type": "application/octet-stream",
            },
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=settings.autodesk_upload_timeout_seconds,
            ) as response:
                response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise AutodeskAPIError(
                f"Autodesk signed S3 upload failed with HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise AutodeskAPIError(f"Autodesk signed S3 upload failed: {exc.reason}") from exc

    def complete_signed_upload(self, bucket_key: str, object_name: str, upload_key: str) -> dict:
        quoted_bucket = urllib.parse.quote(bucket_key, safe="")
        quoted_object = urllib.parse.quote(object_name, safe="")
        url = f"{self._oss_base_url()}/buckets/{quoted_bucket}/objects/{quoted_object}/signeds3upload"

        return self._request_json(
            "POST",
            url,
            {
                "uploadKey": upload_key,
            },
        )

    def start_ifc_job(self, urn: str) -> dict:
        payload = {
            "input": {"urn": urn},
            "output": {
                "formats": [
                    {
                        "type": "ifc",
                    }
                ]
            },
        }
        return self._request_json("POST", f"{self._model_derivative_base_url()}/designdata/job", payload)

    def wait_for_manifest(self, urn: str) -> dict:
        deadline = time.monotonic() + settings.autodesk_model_derivative_timeout_seconds
        poll_interval = max(settings.autodesk_model_derivative_poll_interval_seconds, 1)
        last_manifest: dict = {}

        while time.monotonic() < deadline:
            last_manifest = self.get_manifest(urn)
            status = str(last_manifest.get("status") or "").lower()

            if status in self.SUCCESS_STATUSES:
                return last_manifest

            if status in self.FAILED_STATUSES:
                raise AutodeskModelDerivativeError(
                    f"Autodesk Model Derivative job ended with status {status}: "
                    f"{json.dumps(last_manifest, ensure_ascii=True)}"
                )

            if status and status not in self.RUNNING_STATUSES:
                raise AutodeskModelDerivativeError(
                    f"Autodesk Model Derivative job returned unknown status {status}."
                )

            time.sleep(poll_interval)

        raise AutodeskModelDerivativeError(
            "Autodesk Model Derivative job did not finish within "
            f"{settings.autodesk_model_derivative_timeout_seconds} seconds: "
            f"{json.dumps(last_manifest, ensure_ascii=True)}"
        )

    def get_manifest(self, urn: str) -> dict:
        quoted_urn = urllib.parse.quote(urn, safe="")
        return self._request_json(
            "GET",
            f"{self._model_derivative_base_url()}/designdata/{quoted_urn}/manifest",
        )

    def find_ifc_derivative_urn(self, manifest: dict) -> str:
        candidates: list[tuple[int, str]] = []

        def walk(node: object) -> None:
            if isinstance(node, dict):
                urn = node.get("urn")
                if isinstance(urn, str):
                    marker_values = [
                        str(node.get("outputType") or ""),
                        str(node.get("role") or ""),
                        str(node.get("mime") or ""),
                        str(node.get("type") or ""),
                        urn,
                    ]
                    marker = " ".join(marker_values).lower()
                    if "ifc" in marker:
                        score = 0
                        if str(node.get("role") or "").lower() == "ifc":
                            score += 3
                        if str(node.get("outputType") or "").lower() == "ifc":
                            score += 2
                        if urn.lower().endswith(".ifc"):
                            score += 1
                        candidates.append((score, urn))

                for value in node.values():
                    if isinstance(value, (dict, list)):
                        walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(manifest)

        if not candidates:
            raise AutodeskModelDerivativeError(
                f"Autodesk manifest did not include an IFC derivative: "
                f"{json.dumps(manifest, ensure_ascii=True)}"
            )

        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def download_derivative(self, urn: str, derivative_urn: str, output_path: str | Path) -> Path:
        quoted_urn = urllib.parse.quote(urn, safe="")
        quoted_derivative_urn = urllib.parse.quote(derivative_urn, safe="")
        url = (
            f"{self._model_derivative_base_url()}/designdata/{quoted_urn}"
            f"/manifest/{quoted_derivative_urn}"
        )
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(self._request_bytes("GET", url))
        return destination

    def _request_json(
        self,
        method: str,
        url: str,
        payload: dict | None = None,
        data: bytes | None = None,
        content_type: str = "application/json",
    ) -> dict:
        body = data if data is not None else json.dumps(payload).encode("utf-8") if payload is not None else None
        response_body = self._request_bytes(
            method,
            url,
            data=body,
            content_type=content_type,
            accept="application/json",
        )
        if not response_body:
            return {}
        return json.loads(response_body.decode("utf-8"))

    def _request_bytes(
        self,
        method: str,
        url: str,
        data: bytes | None = None,
        content_type: str = "application/json",
        accept: str = "*/*",
    ) -> bytes:
        token = self.auth_client.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": accept,
        }
        if data is not None:
            headers["Content-Type"] = content_type

        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers=headers,
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=settings.autodesk_http_timeout_seconds,
            ) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise AutodeskAPIError(
                f"Autodesk request failed with HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise AutodeskAPIError(f"Autodesk request failed: {exc.reason}") from exc

    def _oss_base_url(self) -> str:
        return settings.autodesk_oss_base_url.rstrip("/")

    def _model_derivative_base_url(self) -> str:
        return settings.autodesk_model_derivative_base_url.rstrip("/")

    @staticmethod
    def _urn_from_object_id(object_id: str) -> str:
        encoded = base64.urlsafe_b64encode(object_id.encode("utf-8")).decode("ascii")
        return encoded.rstrip("=")
