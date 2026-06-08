import os
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Production-ready settings with environment-based overrides."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ============ Database ============
    database_url: str
    
    # ============ API Keys & Secrets ============
    gemini_api_key: str = ""
    tavily_api_key: str = ""
    claimsense_auth_secret: str
    
    # ============ Authentication ============
    claimsense_demo_user: str = "adjuster"
    claimsense_demo_password: str = ""  # MUST be set in production
    
    # ============ CORS & Security ============
    cors_origins: str = "http://localhost:3000,http://localhost:8000"  # comma-separated
    environment: str = "development"  # development, staging, production
    
    # ============ Models & Processing ============
    gemini_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "models/gemini-embedding-002"
    
    # ============ File Paths ============
    upload_dir: Path = Path("./uploads")
    reports_dir: Path = Path("./reports")
    
    # ============ Processing Settings ============
    min_text_chars_per_page: int = 40
    
    # ============ JWT Settings ============
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24 * 7  # 7 days
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL is provided and properly formatted."""
        if not v or v.strip() == "":
            raise ValueError("DATABASE_URL must be set in environment")
        return v
    
    @field_validator("claimsense_auth_secret")
    @classmethod
    def validate_auth_secret(cls, v: str) -> str:
        """Ensure auth secret is strong enough."""
        if not v or len(v) < 32:
            raise ValueError(
                "CLAIMSENSE_AUTH_SECRET must be set and at least 32 characters long. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        return v
    
    @field_validator("claimsense_demo_password")
    @classmethod
    def validate_demo_password(cls, v: str) -> str:
        """Ensure demo password is set."""
        if not v or v.strip() == "":
            raise ValueError(
                "CLAIMSENSE_DEMO_PASSWORD must be set in production. "
                "Use a strong password or set it via environment variable."
            )
        return v
    
    @field_validator("gemini_api_key")
    @classmethod
    def validate_gemini_key(cls, v: str) -> str:
        """Normalize the Gemini API key when present.

        Gemini features are optional in development; when the key is missing or invalid,
        the application uses local deterministic fallbacks so the rest of the product keeps working.
        """
        return (v or "").strip()
    
    def get_cors_origins(self) -> list[str]:
        """Parse comma-separated CORS origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
