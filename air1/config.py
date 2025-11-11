from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator
from typing import Optional, Literal
from functools import lru_cache
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

    # Environment
    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Application environment"
    )

    # Database settings
    database_host: str = Field(default="localhost", description="Database host")
    database_port: int = Field(
        default=5432, ge=1, le=65535, description="Database port"
    )
    database_name: str = Field(
        default="air1", min_length=1, description="Database name"
    )
    database_user: str = Field(..., min_length=1, description="Database username")
    database_password: Optional[str] = Field(
        default="", description="Database password"
    )

    # Connection pool settings
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

    # LinkedIn settings
    linkedin_sid: Optional[str] = Field(default=None, description="LinkedIn session ID")

    # Logging settings
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

    # Application settings
    app_name: str = Field(default="Air1", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    cors_origins: list[str] = Field(default=["*"], description="CORS allowed origins")

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
        return f"postgresql+asyncpg://{self.database_user}{password}@{self.database_host}:{self.database_port}/{self.database_name}"

    def configure_logging(self) -> None:
        """Configure loguru based on settings"""
        # Remove default handler
        logger.remove()

        # Add console handler
        logger.add(
            sys.stderr, format=self.log_format, level=self.log_level, colorize=True
        )

        # Add file handler if log_file is specified
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


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    settings = Settings()
    settings.configure_logging()
    return settings


settings = get_settings()
