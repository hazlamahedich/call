from sqlmodel import Field
from typing import Optional

from .base import TenantModel

LOGO_STORAGE_TYPE_FIELD = "logo_storage_type"


class AgencyBranding(TenantModel, table=True):
    __tablename__ = "agency_branding"  # type: ignore

    logo_url: Optional[str] = Field(
        default=None, description="Base64 data URL or URL for agency logo"
    )
    logo_storage_type: Optional[str] = Field(
        default=None,
        max_length=16,
        description="Storage type: 'base64' (current) or 's3' (after migration)",
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


# ---------------------------------------------------------------------------
# MIGRATION PATH: base64 logo → S3/cloud storage
# ---------------------------------------------------------------------------
# Current state:  logo_url stores base64 data URLs (data:image/png;base64,...)
#                 logo_storage_type is NULL (treated as 'base64')
#
# Target state:   logo_url stores S3 URLs (https://bucket.s3.amazonaws.com/...)
#                 logo_storage_type = 's3'
#
# Migration steps:
# 1. Add logo_storage_type column (this model already has it)
# 2. Run migration to add column + backfill existing rows:
#      UPDATE agency_branding SET logo_storage_type = 'base64' WHERE logo_url IS NOT NULL;
# 3. Create S3 bucket + presigned upload endpoint
# 4. Create batch script to: read base64 rows → upload to S3 → update logo_url
# 5. Update branding router validation to accept S3 URLs when type='s3'
# 6. Update _validate_logo() in routers/branding.py to handle both types
# 7. After migration: ALTER TABLE agency_branding ALTER logo_url TYPE TEXT;
#    (remove any length constraints if needed)
# ---------------------------------------------------------------------------
