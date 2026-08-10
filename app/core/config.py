import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "DriftWatch"
    APP_VERSION: str = "0.2.0"
    DEBUG: bool = Field(default=True, description="Enable development diagnostics.")
    
    # Upload and security limits
    MAX_UPLOAD_SIZE_MB: int = 25
    MAX_EXTRACTED_SIZE_MB: int = 100
    MAX_FILE_COUNT: int = 500
    MAX_COMPRESSION_RATIO: float = 10.0
    
    # Directories
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "uploads")
    EXTRACTED_DIR: str = os.path.join(BASE_DIR, "extracted")
    
    # Database
    DATABASE_URL: str = f"sqlite:///{os.path.join(BASE_DIR, 'driftwatch.db')}"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DRIFTWATCH_",
        extra="ignore",
        case_sensitive=False,
    )

settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.EXTRACTED_DIR, exist_ok=True)
