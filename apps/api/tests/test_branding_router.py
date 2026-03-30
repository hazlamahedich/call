"""
Story 1-5: White-labeled Admin Portal & Custom Branding
Unit Tests for Branding Router Validation Helpers

Test ID Format: 1.5-API-ROUTER-XXX
Priority: P0 (Critical) | P1 (High) | P2 (Medium)

Tests the pure validation functions directly, avoiding FastAPI DI issues.
"""

import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException


class TestRequireAdmin:
    """[1.5-API-ROUTER-001..003] _require_admin validation"""

    def _make_request(self, user_role=None, org_id=None, auth_header=None):
        request = MagicMock()
        request.state = MagicMock()
        request.state.user_role = user_role
        request.state.org_id = org_id
        if auth_header:
            request.headers.get.return_value = auth_header
        else:
            request.headers.get.return_value = ""
        return request

    def test_admin_via_request_state_passes(self):
        from routers.branding import _require_admin

        request = self._make_request(user_role="org:admin", org_id="org_123")
        _require_admin(request)

    def test_non_admin_rejected(self):
        from routers.branding import _require_admin

        request = self._make_request(user_role="org:member", org_id="org_123")
        with pytest.raises(HTTPException) as exc_info:
            _require_admin(request)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "AUTH_FORBIDDEN"

    def test_no_role_rejected(self):
        from routers.branding import _require_admin

        request = self._make_request(user_role=None, org_id=None)
        with pytest.raises(HTTPException) as exc_info:
            _require_admin(request)
        assert exc_info.value.status_code == 403

    def test_admin_via_jwt_orgs_dict(self):
        import jwt as pyjwt
        from routers.branding import _require_admin

        token = pyjwt.encode(
            {"orgs": {"org_123": {"role": "org:admin"}}}, "secret", algorithm="HS256"
        )
        request = self._make_request(
            user_role="org:member",
            org_id="org_123",
            auth_header=f"Bearer {token}",
        )
        _require_admin(request)

    def test_admin_via_jwt_org_role(self):
        from routers.branding import _require_admin

        import jwt as pyjwt

        token = pyjwt.encode({"org_role": "org:admin"}, "secret", algorithm="HS256")
        request = self._make_request(
            user_role=None,
            org_id="org_123",
            auth_header=f"Bearer {token}",
        )
        _require_admin(request)


class TestValidateLogo:
    """[1.5-API-ROUTER-004..009] _validate_logo validation"""

    def test_valid_png_data_url(self):
        from routers.branding import _validate_logo

        _validate_logo("data:image/png;base64,iVBORw0KGgo=")

    def test_valid_jpeg_data_url(self):
        from routers.branding import _validate_logo

        _validate_logo("data:image/jpeg;base64,/9j/4AAQSkZJRg==")

    def test_valid_svg_data_url(self):
        from routers.branding import _validate_logo

        _validate_logo("data:image/svg+xml;base64,PHN2ZyB4bWxucz0=")

    def test_reject_invalid_prefix(self):
        from routers.branding import _validate_logo

        with pytest.raises(HTTPException) as exc_info:
            _validate_logo("data:image/gif;base64,abc")
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "BRANDING_INVALID_LOGO"

    def test_reject_non_data_url(self):
        from routers.branding import _validate_logo

        with pytest.raises(HTTPException) as exc_info:
            _validate_logo("https://example.com/logo.png")
        assert exc_info.value.status_code == 400

    def test_reject_malformed_data_url(self):
        from routers.branding import _validate_logo

        with pytest.raises(HTTPException) as exc_info:
            _validate_logo("data:image/png;base64")
        assert exc_info.value.status_code == 400
        assert "Malformed" in exc_info.value.detail["message"]

    def test_reject_logo_exceeding_2mb_boundary(self):
        from routers.branding import _validate_logo, MAX_LOGO_SIZE

        oversized_b64 = "A" * int(MAX_LOGO_SIZE * 1.34 + 1)
        data_url = f"data:image/png;base64,{oversized_b64}"
        with pytest.raises(HTTPException) as exc_info:
            _validate_logo(data_url)
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "BRANDING_INVALID_LOGO"
        assert "2MB" in exc_info.value.detail["message"]

    def test_accept_logo_at_2mb_boundary(self):
        from routers.branding import _validate_logo, MAX_LOGO_SIZE

        at_limit_b64 = "A" * int(MAX_LOGO_SIZE * 1.34)
        data_url = f"data:image/png;base64,{at_limit_b64}"
        _validate_logo(data_url)


class TestValidateColor:
    """[1.5-API-ROUTER-010..013] _validate_color validation"""

    def test_valid_hex_color(self):
        from routers.branding import _validate_color

        _validate_color("#10B981")

    def test_valid_hex_uppercase(self):
        from routers.branding import _validate_color

        _validate_color("#ABCDEF")

    def test_reject_no_hash(self):
        from routers.branding import _validate_color

        with pytest.raises(HTTPException) as exc_info:
            _validate_color("10B981")
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "BRANDING_INVALID_COLOR"

    def test_reject_short_hex(self):
        from routers.branding import _validate_color

        with pytest.raises(HTTPException) as exc_info:
            _validate_color("#FFF")
        assert exc_info.value.status_code == 400

    def test_reject_named_color(self):
        from routers.branding import _validate_color

        with pytest.raises(HTTPException) as exc_info:
            _validate_color("red")
        assert exc_info.value.status_code == 400


class TestDomainRegex:
    """[1.5-API-ROUTER-014..017] DOMAIN_RE validation"""

    def test_valid_domain(self):
        from routers.branding import DOMAIN_RE

        assert DOMAIN_RE.match("example.com") is not None

    def test_valid_subdomain(self):
        from routers.branding import DOMAIN_RE

        assert DOMAIN_RE.match("custom.example.com") is not None

    def test_reject_empty_string(self):
        from routers.branding import DOMAIN_RE

        assert DOMAIN_RE.match("") is None

    def test_reject_invalid_chars(self):
        from routers.branding import DOMAIN_RE

        assert DOMAIN_RE.match("invalid domain.com") is None
        assert DOMAIN_RE.match("invalid$.com") is None
