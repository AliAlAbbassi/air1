from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator
from typing import Optional, Literal
from loguru import logger
import sys


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Application environment"
    )

    database_host: str = Field(default="localhost", description="Database host")
    database_port: int = Field(
        default=5432, ge=1, le=65535, description="Database port"
    )
    database_name: str = Field(
        default="air1", min_length=1, description="Database name"
    )
    database_user: str = Field(default="postgres", min_length=1, description="Database username")
    database_password: Optional[str] = Field(
        default="postgres", description="Database password"
    )

    database_pool_min: int = Field(
        default=10, ge=1, le=100, description="Minimum database pool size"
    )
    database_pool_max: int = Field(
        default=20, ge=1, le=100, description="Maximum database pool size"
    )
    database_pool_timeout: int = Field(
        default=60, ge=1, le=300, description="Database pool timeout in seconds"
    )
    database_echo: bool = Field(
        default=False, description="Echo SQL queries (for debugging)"
    )

    linkedin_sid: Optional[str] = Field(default=None, description="LinkedIn session ID")

    # Email configuration
    resend_api_key: Optional[str] = Field(default=None, description="Resend API key")
    email_from_address: str = Field(default="noreply@yourdomain.com", description="From email address")
    email_from_name: str = Field(default="Air1 Lead Generation", description="From name for emails")

    # Email batching and rate limiting configuration
    email_batch_size: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Number of emails to send in each batch"
    )
    email_delay_between_batches: float = Field(
        default=60.0,
        ge=0,
        le=3600,
        description="Delay in seconds between email batches (prevents rate limiting)"
    )
    email_delay_between_emails: float = Field(
        default=2.0,
        ge=0,
        le=60,
        description="Delay in seconds between individual emails within a batch"
    )
    email_max_concurrent: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum number of concurrent email sends"
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    log_format: str = Field(
        default="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
        description="Log format string",
    )
    log_rotation: str = Field(default="100 MB", description="Log file rotation size")
    log_retention: str = Field(default="10 days", description="Log retention period")
    log_file: Optional[str] = Field(default="logs/app.log", description="Log file path")

    app_name: str = Field(default="Air1", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    cors_origins: list[str] = Field(default=["*"], description="CORS allowed origins")

    # JWT configuration
    jwt_secret: str = Field(
        default="dev-secret-change-in-production",
        description="Secret key for JWT token signing"
    )
    jwt_expiry_hours: int = Field(
        default=168,  # 7 days
        ge=1,
        description="JWT token expiry in hours"
    )

    @field_validator("database_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @model_validator(mode="after")
    def validate_pool_sizes(self) -> "Settings":
        """Ensure max pool size is greater than min pool size"""
        if self.database_pool_max < self.database_pool_min:
            raise ValueError(
                "database_pool_max must be greater than or equal to database_pool_min"
            )
        return self

    @property
    def database_url(self) -> str:
        """Standard database URL for synchronous connections"""
        password = f":{self.database_password}" if self.database_password else ""
        return f"postgresql://{self.database_user}{password}@{self.database_host}:{self.database_port}/{self.database_name}"

    @property
    def async_database_url(self) -> str:
        """Async database URL for SQLModel/SQLAlchemy async connections"""
        password = f":{self.database_password}" if self.database_password else ""
        return f"postgresql+asyncpg://{self.database_user}{password}@{self.database_host}:{self.database_port}/{self.database_name}?sslmode=disable"

    def configure_logging(self) -> None:
        """Configure loguru based on settings"""
        logger.remove()

        logger.add(
            sys.stderr, format=self.log_format, level=self.log_level, colorize=True
        )

        if self.log_file:
            logger.add(
                self.log_file,
                format=self.log_format,
                level=self.log_level,
                rotation=self.log_rotation,
                retention=self.log_retention,
                compression="zip",
            )

        logger.info(f"Logging configured for {self.environment} environment")


def get_settings() -> Settings:
    """Get cached settings instance"""
    settings = Settings()
    settings.configure_logging()
    return settings


settings = get_settings()
