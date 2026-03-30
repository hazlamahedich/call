import json
import logging
from fastapi import APIRouter, Request, HTTPException, status
from svix.webhooks import Webhook
from svix.exceptions import WebhookVerificationError
from typing import Any
from sqlalchemy import text

from config.settings import settings
from database.session import AsyncSessionLocal, set_tenant_context
from models.agency_branding import AgencyBranding
from models.client import Client
from services.base import TenantService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
logger = logging.getLogger(__name__)

_branding_service = TenantService[AgencyBranding](AgencyBranding)
_client_service = TenantService[Client](Client)


@router.post("/clerk")
async def handle_clerk_webhook(request: Request):
    webhook_secret = settings.CLERK_WEBHOOK_SECRET
    if not webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured",
        )

    payload = await request.body()
    headers = dict(request.headers)

    wh = Webhook(webhook_secret)

    try:
        evt = wh.verify(payload, headers)
    except WebhookVerificationError as e:
        logger.error(f"Webhook verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature"
        )

    event_type = evt.get("type")
    data = evt.get("data", {})

    logger.info(f"Received Clerk webhook: {event_type}")

    if event_type == "organization.created":
        await handle_organization_created(data)
    elif event_type == "organization.updated":
        await handle_organization_updated(data)
    elif event_type == "organization.deleted":
        await handle_organization_deleted(data)
    elif event_type == "organizationMembership.created":
        await handle_membership_created(data)
    elif event_type == "organizationMembership.updated":
        await handle_membership_updated(data)
    elif event_type == "organizationMembership.deleted":
        await handle_membership_deleted(data)
    else:
        logger.info(f"Unhandled webhook event type: {event_type}")

    return {"received": True}


async def handle_organization_created(data: dict[str, Any]) -> None:
    org_id = data.get("id")
    name = data.get("name")
    slug = data.get("slug")

    logger.info(f"Organization created: {org_id} - {name}")

    if not org_id:
        logger.warning("organization.created event missing id, skipping")
        return

    async with AsyncSessionLocal() as session:
        await set_tenant_context(session, org_id)

        branding = AgencyBranding()
        if name:
            branding.brand_name = name
        try:
            await _branding_service.create(session, branding)
            await session.commit()
            logger.info(f"Created default branding for org {org_id}")
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create branding for org {org_id}: {e}")


async def handle_organization_updated(data: dict[str, Any]) -> None:
    org_id = data.get("id")
    name = data.get("name")

    logger.info(f"Organization updated: {org_id} - {name}")

    if not org_id:
        return

    async with AsyncSessionLocal() as session:
        await set_tenant_context(session, org_id)

        try:
            rows = await _branding_service.list_all(session, limit=1)
            if rows:
                branding = rows[0]
                if name:
                    branding.brand_name = name
                await _branding_service.update(session, branding)
                await session.commit()
                logger.info(f"Updated branding for org {org_id}")
            else:
                logger.warning(
                    f"No branding row found for org {org_id} on update, creating"
                )
                branding = AgencyBranding()
                if name:
                    branding.brand_name = name
                await _branding_service.create(session, branding)
                await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to update branding for org {org_id}: {e}")


async def handle_organization_deleted(data: dict[str, Any]) -> None:
    org_id = data.get("id")

    logger.info(f"Organization deleted: {org_id}")

    if not org_id:
        return

    async with AsyncSessionLocal() as session:
        await session.execute(
            text("SELECT set_config('app.is_platform_admin', 'true', true)")
        )
        try:
            rows = await _branding_service.list_all(session, limit=100)
            for row in rows:
                if row.id is not None:
                    await _branding_service.mark_soft_deleted(session, row.id)
            await session.commit()
            logger.info(f"Soft-deleted branding for org {org_id}")
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to soft-delete branding for org {org_id}: {e}")


async def handle_membership_created(data: dict[str, Any]) -> None:
    org_id = data.get("organization", {}).get("id")
    user_id = data.get("public_user_data", {}).get("user_id")
    role = data.get("role")

    logger.info(f"Membership created: org={org_id}, user={user_id}, role={role}")
    logger.info("Membership tracking not yet implemented — no membership table exists")


async def handle_membership_updated(data: dict[str, Any]) -> None:
    org_id = data.get("organization", {}).get("id")
    user_id = data.get("public_user_data", {}).get("user_id")
    role = data.get("role")

    logger.info(f"Membership updated: org={org_id}, user={user_id}, role={role}")
    logger.info("Membership tracking not yet implemented — no membership table exists")


async def handle_membership_deleted(data: dict[str, Any]) -> None:
    org_id = data.get("organization", {}).get("id")
    user_id = data.get("public_user_data", {}).get("user_id")

    logger.info(f"Membership deleted: org={org_id}, user={user_id}")
    logger.info("Membership tracking not yet implemented — no membership table exists")
