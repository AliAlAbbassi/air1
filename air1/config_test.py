import pytest
from air1.config import Settings
from pydantic import ValidationError


@pytest.mark.unit
class TestSettings:
    """Unit tests for Settings configuration."""

    def test_settings_with_valid_env(self, monkeypatch):
        """Test settings with valid environment variables."""
        monkeypatch.setenv("DATABASE_HOST", "testhost")
        monkeypatch.setenv("DATABASE_PORT", "5433")
        monkeypatch.setenv("DATABASE_NAME", "testdb")
        monkeypatch.setenv("DATABASE_USER", "testuser")
        monkeypatch.setenv("DATABASE_PASSWORD", "testpass")

        settings = Settings()

        assert settings.database_host == "testhost"
        assert settings.database_port == 5433
        assert settings.database_name == "testdb"
        assert settings.database_user == "testuser"
        assert settings.database_password == "testpass"

    def test_settings_default_values(self, monkeypatch):
        """Test settings with default values."""
        monkeypatch.setenv("DATABASE_USER", "testuser")  # Required field

        settings = Settings()

        assert settings.database_host == "localhost"
        assert settings.database_port == 5432
        assert settings.database_name == "air1"
        assert settings.database_pool_min == 10
        assert settings.database_pool_max == 20
        assert settings.database_pool_timeout == 60

    def test_invalid_port_validation(self, monkeypatch):
        """Test port validation."""
        monkeypatch.setenv("DATABASE_USER", "testuser")

        # Port too high
        monkeypatch.setenv("DATABASE_PORT", "70000")
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        assert "less than or equal to 65535" in str(exc_info.value)

        # Port too low
        monkeypatch.setenv("DATABASE_PORT", "0")
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_database_url_property(self, monkeypatch):
        """Test database URL generation."""
        monkeypatch.setenv("DATABASE_HOST", "dbhost")
        monkeypatch.setenv("DATABASE_PORT", "5433")
        monkeypatch.setenv("DATABASE_NAME", "mydb")
        monkeypatch.setenv("DATABASE_USER", "dbuser")
        monkeypatch.setenv("DATABASE_PASSWORD", "dbpass")

        settings = Settings()

        expected_url = "postgresql://dbuser:dbpass@dbhost:5433/mydb"
        assert settings.database_url == expected_url

    def test_database_url_without_password(self, monkeypatch):
        """Test database URL generation without password."""
        monkeypatch.setenv("DATABASE_USER", "dbuser")
        monkeypatch.setenv("DATABASE_PASSWORD", "")

        settings = Settings()

        expected_url = "postgresql://dbuser@localhost:5432/air1"
        assert settings.database_url == expected_url

    def test_async_database_url_property(self, monkeypatch):
        """Test async database URL generation."""
        monkeypatch.setenv("DATABASE_HOST", "dbhost")
        monkeypatch.setenv("DATABASE_PORT", "5433")
        monkeypatch.setenv("DATABASE_NAME", "mydb")
        monkeypatch.setenv("DATABASE_USER", "dbuser")
        monkeypatch.setenv("DATABASE_PASSWORD", "dbpass")

        settings = Settings()

        expected_url = "postgresql+asyncpg://dbuser:dbpass@dbhost:5433/mydb"
        assert settings.async_database_url == expected_url

    def test_linkedin_sid_optional(self, monkeypatch):
        """Test that LinkedIn SID is optional."""
        monkeypatch.setenv("DATABASE_USER", "testuser")
        # Clear the linkedin_sid from .env file
        monkeypatch.delenv("LINKEDIN_SID", raising=False)

        # Create settings without env file
        settings = Settings(_env_file=None)
        assert settings.linkedin_sid is None

        monkeypatch.setenv("LINKEDIN_SID", "test_session_id")
        settings = Settings(_env_file=None)
        assert settings.linkedin_sid == "test_session_id"

    def test_case_insensitive_env_vars(self, monkeypatch):
        """Test that environment variable names are case-insensitive."""
        monkeypatch.setenv("database_user", "testuser")
        monkeypatch.setenv("DATABASE_HOST", "testhost")
        monkeypatch.setenv("DaTaBaSe_PoRt", "5433")

        settings = Settings()

        assert settings.database_user == "testuser"
        assert settings.database_host == "testhost"
        assert settings.database_port == 5433
