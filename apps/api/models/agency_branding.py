from sqlmodel import Field
from typing import Optional

from .base import TenantModel


class AgencyBranding(TenantModel, table=True):
    __tablename__ = "agency_branding"  # type: ignore

    logo_url: Optional[str] = Field(
        default=None, description="Base64 data URL or URL for agency logo"
    )
    primary_color: str = Field(
        default="#10B981", max_length=7, description="Primary hex color"
    )
    custom_domain: Optional[str] = Field(
        default=None, max_length=255, description="Custom CNAME domain"
    )
    domain_verified: bool = Field(
        default=False, description="Whether custom domain DNS is verified"
    )
    brand_name: Optional[str] = Field(
        default=None, max_length=255, description="Display name for the agency"
    )
