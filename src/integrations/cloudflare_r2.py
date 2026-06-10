from functools import lru_cache
from pathlib import Path
from typing import BinaryIO
import boto3
from botocore.client import BaseClient
from botocore.config import Config
from src.core.config import settings

class CloudflareR2ConfigError(RuntimeError):
    pass

def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class CloudflareR2Client:
    def __init__(self) -> None:
        self._client: BaseClient | None = None

    @property
    def bucket_name(self) -> str:
        bucket_name = _clean(settings.cloudflare_r2_bucket_name)
        if not bucket_name:
            raise CloudflareR2ConfigError("CLOUDFLARE_R2_BUCKET_NAME is required.")
        return bucket_name

    @property
    def endpoint_url(self) -> str:
        endpoint_url = _clean(settings.cloudflare_r2_endpoint_url)
        if endpoint_url:
            return endpoint_url.rstrip("/")

        account_id = _clean(settings.cloudflare_r2_account_id)
        if not account_id:
            raise CloudflareR2ConfigError(
                "CLOUDFLARE_R2_ACCOUNT_ID or CLOUDFLARE_R2_ENDPOINT_URL is required."
            )

        return f"https://{account_id}.r2.cloudflarestorage.com"

    def _validate_credentials(self) -> None:
        if not _clean(settings.cloudflare_r2_access_key_id):
            raise CloudflareR2ConfigError("CLOUDFLARE_R2_ACCESS_KEY_ID is required.")

        if not _clean(settings.cloudflare_r2_secret_access_key):
            raise CloudflareR2ConfigError("CLOUDFLARE_R2_SECRET_ACCESS_KEY is required.")

    def client(self) -> BaseClient:
        self._validate_credentials()

        if self._client is None:
            self._client = boto3.client(
                service_name="s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=settings.cloudflare_r2_access_key_id,
                aws_secret_access_key=settings.cloudflare_r2_secret_access_key,
                region_name=settings.cloudflare_r2_region,
                config=Config(signature_version="s3v4"),
            )

        return self._client

    def build_key(self, filename: str, prefix: str = "ifc-uploads") -> str:
        safe_filename = Path(filename).name
        clean_prefix = prefix.strip("/")

        if not clean_prefix:
            return safe_filename

        return f"{clean_prefix}/{safe_filename}"

    def upload_fileobj(
        self,
        fileobj: BinaryIO,
        filename: str,
        key: str | None = None,
        content_type: str | None = None,
    ) -> str:
        object_key = key or self.build_key(filename)

        extra_args = {"ContentType": content_type} if content_type else None
        upload_kwargs = {"ExtraArgs": extra_args} if extra_args else {}

        self.client().upload_fileobj(
            Fileobj=fileobj,
            Bucket=self.bucket_name,
            Key=object_key,
            **upload_kwargs,
        )

        return object_key

    def upload_bytes(
        self,
        content: bytes,
        filename: str,
        key: str | None = None,
        content_type: str | None = None,
    ) -> str:
        object_key = key or self.build_key(filename)
        extra_args = {"ContentType": content_type} if content_type else {}

        self.client().put_object(
            Bucket=self.bucket_name,
            Key=object_key,
            Body=content,
            **extra_args,
        )

        return object_key

    def download_file(self, key: str, destination: str | Path) -> Path:
        destination_path = Path(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        self.client().download_file(
            Bucket=self.bucket_name,
            Key=key,
            Filename=str(destination_path),
        )

        return destination_path

    def presigned_get_url(self, key: str, expires_in: int = 3600) -> str:
        return self.client().generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )

    def presigned_put_url(self, key: str, expires_in: int = 3600) -> str:
        return self.client().generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )

    def public_url(self, key: str) -> str | None:
        public_base_url = _clean(settings.cloudflare_r2_public_base_url)
        if not public_base_url:
            return None

        return f"{public_base_url.rstrip('/')}/{key.lstrip('/')}"

    def delete_object(self, key: str) -> None:
        self.client().delete_object(Bucket=self.bucket_name, Key=key)


@lru_cache
def get_cloudflare_r2_client() -> CloudflareR2Client:
    return CloudflareR2Client()
