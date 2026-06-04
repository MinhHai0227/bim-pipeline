from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Application settings
    app_name: str = "BIM Pipeline API"
    environment: str = "local"
    
    # Database settings
    database_url: str 

    # Cloudflare R2 object storage settings
    cloudflare_r2_account_id: str 
    cloudflare_r2_access_key_id: str 
    cloudflare_r2_secret_access_key: str 
    cloudflare_r2_bucket_name: str 
    cloudflare_r2_endpoint_url: str 
    cloudflare_r2_public_base_url: str
    cloudflare_r2_region: str = "auto"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
