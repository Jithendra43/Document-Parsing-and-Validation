"""Configuration management for the EDI processing microservice."""

import os
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "EDI X12 278 Processor"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    
    # Streamlit Configuration
    streamlit_host: str = Field(default="0.0.0.0", env="STREAMLIT_HOST")
    streamlit_port: int = Field(default=8501, env="STREAMLIT_PORT")
    
    # File Processing
    max_file_size: int = Field(default=50 * 1024 * 1024, env="MAX_FILE_SIZE")  # 50MB
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")
    output_dir: str = Field(default="./outputs", env="OUTPUT_DIR")
    temp_dir: str = Field(default="./temp", env="TEMP_DIR")
    
    # Database
    database_url: str = Field(default="sqlite:///./edi_processor.db", env="DATABASE_URL")
    
    # Redis (for caching and session management)
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # AI Configuration - GROQ ONLY
    groq_api_key: Optional[str] = Field(default=None, env="GROQ_API_KEY")
    ai_model: str = Field(default="llama-3.1-8b-instant", env="AI_MODEL")
    
    # FHIR Configuration
    fhir_base_url: str = Field(default="http://localhost:8080/fhir", env="FHIR_BASE_URL")
    fhir_version: str = Field(default="R4", env="FHIR_VERSION")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Security
    secret_key: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")
    allowed_origins: List[str] = Field(default=["*"], env="ALLOWED_ORIGINS")
    
    # EDI Processing
    validate_segments: bool = Field(default=True, env="VALIDATE_SEGMENTS")
    strict_validation: bool = Field(default=False, env="STRICT_VALIDATION")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"  # Allow extra fields from .env
    }


# Global settings instance
settings = Settings()


def ensure_directories():
    """Ensure required directories exist."""
    directories = [
        settings.upload_dir,
        settings.output_dir,
        settings.temp_dir,
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True) 