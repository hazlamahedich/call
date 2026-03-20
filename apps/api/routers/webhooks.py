import json
import logging
from fastapi import APIRouter, Request, HTTPException, status, Depends
from svix.webhooks import Webhook
from svix.exceptions import WebhookVerificationError
from typing import Any

from config.settings import settings

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
logger = logging.getLogger(__name__)


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
    public_metadata = data.get("public_metadata", {})

    logger.info(f"Organization created: {org_id} - {name}")

    # TODO: Sync to local database
    # This will be implemented when database models are added


async def handle_organization_updated(data: dict[str, Any]) -> None:
    org_id = data.get("id")
    name = data.get("name")

    logger.info(f"Organization updated: {org_id} - {name}")

    # TODO: Update local database record


async def handle_organization_deleted(data: dict[str, Any]) -> None:
    org_id = data.get("id")

    logger.info(f"Organization deleted: {org_id}")

    # TODO: Soft delete in local database


async def handle_membership_created(data: dict[str, Any]) -> None:
    org_id = data.get("organization", {}).get("id")
    user_id = data.get("public_user_data", {}).get("user_id")
    role = data.get("role")

    logger.info(f"Membership created: org={org_id}, user={user_id}, role={role}")

    # TODO: Sync membership to local database


async def handle_membership_updated(data: dict[str, Any]) -> None:
    org_id = data.get("organization", {}).get("id")
    user_id = data.get("public_user_data", {}).get("user_id")
    role = data.get("role")

    logger.info(f"Membership updated: org={org_id}, user={user_id}, role={role}")

    # TODO: Update membership in local database


async def handle_membership_deleted(data: dict[str, Any]) -> None:
    org_id = data.get("organization", {}).get("id")
    user_id = data.get("public_user_data", {}).get("user_id")

    logger.info(f"Membership deleted: org={org_id}, user={user_id}")

    # TODO: Remove membership from local database
