import logging
import re
from typing import Optional

import jwt as pyjwt
from fastapi import APIRouter, HTTPException, Request, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.session import get_session, set_tenant_context
from models.agency_branding import AgencyBranding
from services.base import TenantService
from services.domain_verification import verify_cname

router = APIRouter(prefix="/branding", tags=["Branding"])
logger = logging.getLogger(__name__)

_branding_service = TenantService[AgencyBranding](AgencyBranding)

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)
MAX_LOGO_SIZE = 2 * 1024 * 1024
ALLOWED_LOGO_PREFIXES = ("data:image/png", "data:image/jpeg", "data:image/svg+xml")


def _require_admin(request: Request) -> None:
    user_role = getattr(request.state, "user_role", None)
    if user_role == "org:admin":
        return
    org_id = getattr(request.state, "org_id", None)
    if org_id:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            try:
                token = auth_header[7:]
                payload = pyjwt.decode(
                    token, options={"verify_signature": False, "verify_aud": False}
                )
                orgs = payload.get("orgs")
                if isinstance(orgs, dict):
                    org_role = orgs.get(org_id, {}).get("role")
                else:
                    org_role = payload.get("org_role")
                if org_role == "org:admin":
                    return
            except Exception:
                pass
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "AUTH_FORBIDDEN", "message": "Admin access required"},
    )


def _validate_logo(logo_url: str) -> None:
    if not any(logo_url.startswith(prefix) for prefix in ALLOWED_LOGO_PREFIXES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BRANDING_INVALID_LOGO",
                "message": "Logo must be a PNG, JPEG, or SVG data URL",
            },
        )
    parts = logo_url.split(",", 1)
    if len(parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BRANDING_INVALID_LOGO",
                "message": "Malformed data URL",
            },
        )
    if len(parts[1]) > MAX_LOGO_SIZE * 1.34:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BRANDING_INVALID_LOGO",
                "message": "Logo exceeds maximum size (2MB)",
            },
        )


def _validate_color(color: str) -> None:
    if not HEX_COLOR_RE.match(color):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BRANDING_INVALID_COLOR",
                "message": "Color must be a valid 7-character hex code (#RRGGBB)",
            },
        )


@router.get("")
async def get_branding(request: Request, session: AsyncSession = Depends(get_session)):
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "AUTH_FORBIDDEN",
                "message": "Organization context required",
            },
        )

    await set_tenant_context(session, org_id)
    results = await _branding_service.list_all(session, limit=1)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BRANDING_NOT_FOUND", "message": "No branding configured"},
        )
    return results[0].model_dump(by_alias=True)


@router.put("")
async def update_branding(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "AUTH_FORBIDDEN",
                "message": "Organization context required",
            },
        )

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BRANDING_INVALID_BODY",
                "message": "Invalid JSON body",
            },
        )

    logo_url = body.get("logoUrl")
    primary_color = body.get("primaryColor")
    custom_domain = body.get("customDomain")
    brand_name = body.get("brandName")

    if primary_color is not None:
        _validate_color(primary_color)
    if logo_url is not None:
        _validate_logo(logo_url)
    if custom_domain is not None and custom_domain != "":
        if not DOMAIN_RE.match(custom_domain):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "BRANDING_INVALID_DOMAIN",
                    "message": "Invalid domain format",
                },
            )

    await set_tenant_context(session, org_id)
    results = await _branding_service.list_all(session, limit=1)

    if results:
        existing = results[0]
        existing.logo_url = logo_url
        existing.primary_color = (
            primary_color if primary_color is not None else existing.primary_color
        )
        existing.custom_domain = custom_domain
        existing.domain_verified = (
            False
            if custom_domain != results[0].custom_domain
            else existing.domain_verified
        )
        existing.brand_name = brand_name
        updated = await _branding_service.update(session, existing)
        return updated.model_dump(by_alias=True)
    else:
        if custom_domain and not DOMAIN_RE.match(custom_domain):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "BRANDING_INVALID_DOMAIN",
                    "message": "Invalid domain format",
                },
            )
        record = AgencyBranding(
            logo_url=logo_url,
            primary_color=primary_color or "#10B981",
            custom_domain=custom_domain,
            brand_name=brand_name,
        )
        created = await _branding_service.create(session, record)
        return created.model_dump(by_alias=True)


@router.post("/verify-domain")
async def verify_domain(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "AUTH_FORBIDDEN",
                "message": "Organization context required",
            },
        )

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BRANDING_INVALID_BODY",
                "message": "Invalid JSON body",
            },
        )

    domain = body.get("domain", "").strip()

    if not domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BRANDING_DOMAIN_VERIFICATION_FAILED",
                "message": "Domain is required",
            },
        )

    if not DOMAIN_RE.match(domain):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BRANDING_INVALID_DOMAIN",
                "message": "Invalid domain format",
            },
        )

    result = await verify_cname(domain, settings.BRANDING_CNAME_TARGET)

    if result.verified:
        await set_tenant_context(session, org_id)
        results = await _branding_service.list_all(session, limit=1)
        if results:
            results[0].domain_verified = True
            await _branding_service.update(session, results[0])
        else:
            record = AgencyBranding(
                custom_domain=domain,
                domain_verified=True,
                primary_color="#10B981",
            )
            await _branding_service.create(session, record)

    return {
        "verified": result.verified,
        "message": result.message,
        "instructions": result.instructions,
    }
