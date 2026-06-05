from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Application settings
    app_name: str = "BIM Pipeline API"
    environment: str = "local"
    
    # Database settings
    database_url: str 

    # IFC import settings
    max_ifc_upload_size_mb: int = 500
    tmp_ifc_dir: str = "data/tmp/ifc"

    # Background worker settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    # Fragment conversion worker settings
    fragment_worker_url: str | None = None
    fragment_worker_timeout_seconds: int = 900

    # Cloudflare R2 object storage settings
    cloudflare_r2_account_id: str 
    cloudflare_r2_access_key_id: str 
    cloudflare_r2_secret_access_key: str 
    cloudflare_r2_bucket_name: str 
    cloudflare_r2_endpoint_url: str 
    cloudflare_r2_public_base_url: str
    cloudflare_r2_region: str = "auto"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def resolved_celery_broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def resolved_celery_result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
