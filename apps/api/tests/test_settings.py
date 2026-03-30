"""
Story 1-5: White-labeled Admin Portal & Custom Branding
Unit Tests for Settings Configuration

Test ID Format: 1.5-UNIT-SETTINGS-XXX
Priority: P0 (Critical) | P1 (High) | P2 (Medium)
"""

import os
import pytest
from unittest.mock import patch


class TestSettingsDefaults:
    """[1.5-UNIT-SETTINGS-001..006] Settings class default values"""

    def test_default_project_name(self):
        from config.settings import Settings

        with patch.dict(os.environ, {}, clear=False):
            s = Settings()
        assert s.PROJECT_NAME == "AI Cold Caller API"

    def test_default_database_url(self):
        from config.settings import Settings

        with patch.dict(os.environ, {}, clear=False):
            s = Settings()
        assert s.DATABASE_URL == "sqlite:///./app.db"

    def test_default_secret_key(self):
        from config.settings import Settings

        with patch.dict(os.environ, {}, clear=False):
            s = Settings()
        assert s.SECRET_KEY == "supersecretkey"

    def test_default_algorithm(self):
        from config.settings import Settings

        with patch.dict(os.environ, {}, clear=False):
            s = Settings()
        assert s.ALGORITHM == "HS256"

    def test_default_access_token_expire_minutes(self):
        from config.settings import Settings

        with patch.dict(os.environ, {}, clear=False):
            s = Settings()
        assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 30

    def test_default_branding_cname_target(self):
        from config.settings import Settings

        with patch.dict(os.environ, {}, clear=False):
            s = Settings()
        assert s.BRANDING_CNAME_TARGET == "cname.call.app"


class TestSettingsEnvOverride:
    """[1.5-UNIT-SETTINGS-007..012] Settings loaded from environment variables"""

    def test_project_name_from_env(self):
        from config.settings import Settings

        with patch.dict(os.environ, {"PROJECT_NAME": "Custom API"}):
            s = Settings()
        assert s.PROJECT_NAME == "Custom API"

    def test_database_url_from_env(self):
        from config.settings import Settings

        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db"}
        ):
            s = Settings()
        assert s.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost/db"

    def test_secret_key_from_env(self):
        from config.settings import Settings

        with patch.dict(os.environ, {"SECRET_KEY": "my-super-secret"}):
            s = Settings()
        assert s.SECRET_KEY == "my-super-secret"

    def test_clerk_settings_from_env(self):
        from config.settings import Settings

        with patch.dict(
            os.environ,
            {
                "CLERK_SECRET_KEY": "sk_test_123",
                "CLERK_JWKS_URL": "https://custom.clerk.dev/v1/jwks",
                "CLERK_WEBHOOK_SECRET": "whsec_123",
            },
        ):
            s = Settings()
        assert s.CLERK_SECRET_KEY == "sk_test_123"
        assert s.CLERK_JWKS_URL == "https://custom.clerk.dev/v1/jwks"
        assert s.CLERK_WEBHOOK_SECRET == "whsec_123"

    def test_branding_cname_target_from_env(self):
        from config.settings import Settings

        with patch.dict(os.environ, {"BRANDING_CNAME_TARGET": "custom.call.app"}):
            s = Settings()
        assert s.BRANDING_CNAME_TARGET == "custom.call.app"

    def test_access_token_expire_from_env(self):
        from config.settings import Settings

        with patch.dict(os.environ, {"ACCESS_TOKEN_EXPIRE_MINUTES": "60"}):
            s = Settings()
        assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 60


class TestSettingsTypes:
    """[1.5-UNIT-SETTINGS-013..015] Settings field type validation"""

    def test_access_token_expire_is_int(self):
        from config.settings import Settings

        with patch.dict(os.environ, {"ACCESS_TOKEN_EXPIRE_MINUTES": "120"}):
            s = Settings()
        assert isinstance(s.ACCESS_TOKEN_EXPIRE_MINUTES, int)

    def test_all_string_fields_are_strings(self):
        from config.settings import Settings

        with patch.dict(os.environ, {}, clear=False):
            s = Settings()
        assert isinstance(s.PROJECT_NAME, str)
        assert isinstance(s.DATABASE_URL, str)
        assert isinstance(s.SECRET_KEY, str)
        assert isinstance(s.ALGORITHM, str)

    def test_default_clerk_jwks_url(self):
        from config.settings import Settings

        with patch.dict(os.environ, {}, clear=False):
            s = Settings()
        assert s.CLERK_JWKS_URL == "https://api.clerk.dev/v1/jwks"
