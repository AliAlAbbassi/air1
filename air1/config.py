from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    database_host: str = Field(default="localhost", description="Database host")
    database_port: int = Field(default=5432, description="Database port")
    database_name: str = Field(default="air1", description="Database name")
    database_user: str = Field(..., description="Database username")
    database_password: Optional[str] = Field(default="", description="Database password")

    database_pool_min: int = Field(default=10, description="Minimum database pool size")
    database_pool_max: int = Field(default=20, description="Maximum database pool size")
    database_pool_timeout: int = Field(default=60, description="Database pool timeout in seconds")

    linkedin_sid: Optional[str] = Field(default=None, description="LinkedIn session ID")

    @field_validator("database_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @property
    def database_url(self) -> str:
        password = f":{self.database_password}" if self.database_password else ""
        return f"postgresql://{self.database_user}{password}@{self.database_host}:{self.database_port}/{self.database_name}"

    @property
    def async_database_url(self) -> str:
        password = f":{self.database_password}" if self.database_password else ""
        return f"postgresql+asyncpg://{self.database_user}{password}@{self.database_host}:{self.database_port}/{self.database_name}"


settings = Settings()