from __future__ import annotations

import json
from pathlib import Path
from urllib import error, request

from src.core.config import settings


class FragmentWorkerError(RuntimeError):
    pass


class FragmentWorkerClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.base_url = (base_url or settings.fragment_worker_url or "").rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.fragment_worker_timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url)

    def convert_ifc_to_frag(self, input_path: str | Path, output_path: str | Path) -> dict:
        if not self.is_configured:
            raise FragmentWorkerError("FRAGMENT_WORKER_URL is not configured.")

        payload = json.dumps(
            {
                "inputPath": str(input_path),
                "outputPath": str(output_path),
            }
        ).encode("utf-8")

        req = request.Request(
            url=f"{self.base_url}/convert",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise FragmentWorkerError(f"Fragment worker returned HTTP {exc.code}: {message}") from exc
        except error.URLError as exc:
            raise FragmentWorkerError(f"Fragment worker is unavailable: {exc.reason}") from exc
        except TimeoutError as exc:
            raise FragmentWorkerError("Fragment worker conversion timed out.") from exc

        try:
            result = json.loads(body)
        except json.JSONDecodeError as exc:
            raise FragmentWorkerError("Fragment worker returned invalid JSON.") from exc

        if result.get("status") != "ok":
            raise FragmentWorkerError(result.get("message") or "Fragment conversion failed.")

        return result
