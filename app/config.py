"""Configuration management for the EDI processing microservice."""

import os
from typing import Optional, List

# Try to import pydantic_settings, fallback if not available
try:
    from pydantic import Field
    from pydantic_settings import BaseSettings
    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    # Fallback for compatibility
    HAS_PYDANTIC_SETTINGS = False
    from pydantic import BaseModel as BaseSettings, Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "EDI X12 278 Processor"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, env="DEBUG") if HAS_PYDANTIC_SETTINGS else False
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST") if HAS_PYDANTIC_SETTINGS else "0.0.0.0"
    api_port: int = Field(default=8000, env="API_PORT") if HAS_PYDANTIC_SETTINGS else 8000
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX") if HAS_PYDANTIC_SETTINGS else "/api/v1"
    
    # Streamlit Configuration
    streamlit_host: str = Field(default="0.0.0.0", env="STREAMLIT_HOST") if HAS_PYDANTIC_SETTINGS else "0.0.0.0"
    streamlit_port: int = Field(default=8501, env="STREAMLIT_PORT") if HAS_PYDANTIC_SETTINGS else 8501
    
    # File Processing
    max_file_size: int = Field(default=50 * 1024 * 1024, env="MAX_FILE_SIZE") if HAS_PYDANTIC_SETTINGS else 50 * 1024 * 1024  # 50MB
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR") if HAS_PYDANTIC_SETTINGS else "./uploads"
    output_dir: str = Field(default="./outputs", env="OUTPUT_DIR") if HAS_PYDANTIC_SETTINGS else "./outputs"
    temp_dir: str = Field(default="./temp", env="TEMP_DIR") if HAS_PYDANTIC_SETTINGS else "./temp"
    
    # Database
    database_url: str = Field(default="sqlite:///./edi_processor.db", env="DATABASE_URL") if HAS_PYDANTIC_SETTINGS else "sqlite:///./edi_processor.db"
    
    # Redis (for caching and session management)
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL") if HAS_PYDANTIC_SETTINGS else "redis://localhost:6379/0"
    
    # AI Configuration - GROQ ONLY
    groq_api_key: Optional[str] = Field(default=None, env="GROQ_API_KEY") if HAS_PYDANTIC_SETTINGS else os.getenv("GROQ_API_KEY")
    ai_model: str = Field(default="llama-3.1-8b-instant", env="AI_MODEL") if HAS_PYDANTIC_SETTINGS else "llama-3.1-8b-instant"
    
    # FHIR Configuration
    fhir_base_url: str = Field(default="http://localhost:8080/fhir", env="FHIR_BASE_URL") if HAS_PYDANTIC_SETTINGS else "http://localhost:8080/fhir"
    fhir_version: str = Field(default="R4", env="FHIR_VERSION") if HAS_PYDANTIC_SETTINGS else "R4"
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL") if HAS_PYDANTIC_SETTINGS else "INFO"
    log_format: str = Field(default="console", env="LOG_FORMAT") if HAS_PYDANTIC_SETTINGS else "console"  # Changed default from json to console
    
    # Security
    secret_key: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY") if HAS_PYDANTIC_SETTINGS else "your-secret-key-change-in-production"
    allowed_origins: List[str] = Field(default=["*"], env="ALLOWED_ORIGINS") if HAS_PYDANTIC_SETTINGS else ["*"]
    
    # EDI Processing
    validate_segments: bool = Field(default=True, env="VALIDATE_SEGMENTS") if HAS_PYDANTIC_SETTINGS else True
    strict_validation: bool = Field(default=False, env="STRICT_VALIDATION") if HAS_PYDANTIC_SETTINGS else False
    
    def __init__(self, **kwargs):
        """Initialize settings with fallback for environment variables."""
        super().__init__(**kwargs)
        
        # Manual environment variable loading if pydantic_settings not available
        if not HAS_PYDANTIC_SETTINGS:
            self.debug = os.getenv("DEBUG", "false").lower() == "true"
            self.api_host = os.getenv("API_HOST", "0.0.0.0")
            self.api_port = int(os.getenv("API_PORT", "8000"))
            self.streamlit_host = os.getenv("STREAMLIT_HOST", "0.0.0.0")
            self.streamlit_port = int(os.getenv("STREAMLIT_PORT", "8501"))
            self.groq_api_key = os.getenv("GROQ_API_KEY")
            self.log_level = os.getenv("LOG_LEVEL", "INFO")
            self.log_format = os.getenv("LOG_FORMAT", "console")


# Create settings instance with error handling
try:
    settings = Settings()
except Exception as e:
    print(f"Warning: Settings initialization failed: {e}")
    # Create minimal fallback settings
    class FallbackSettings:
        app_name = "EDI X12 278 Processor"
        app_version = "0.1.0"
        debug = False
        api_host = "0.0.0.0"
        api_port = 8000
        streamlit_host = "0.0.0.0"
        streamlit_port = 8501
        max_file_size = 50 * 1024 * 1024
        upload_dir = "./uploads"
        output_dir = "./outputs"
        temp_dir = "./temp"
        groq_api_key = os.getenv("GROQ_API_KEY")
        log_level = "INFO"
        log_format = "console"
        allowed_origins = ["*"]
    
    settings = FallbackSettings()


def ensure_directories():
    """Ensure required directories exist."""
    directories = [
        settings.upload_dir,
        settings.output_dir,
        settings.temp_dir,
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True) 