import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session, set_tenant_context
from models.client import Client
from services.base import TenantService

router = APIRouter(prefix="/organizations/{org_id}/clients", tags=["Clients"])
logger = logging.getLogger(__name__)

_client_service = TenantService[Client](Client)


def _resolve_org_id(request: Request, org_id: str) -> str:
    authenticated_org = getattr(request.state, "org_id", None)
    if authenticated_org and authenticated_org != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "AUTH_FORBIDDEN",
                "message": "Cannot access another organization's clients",
            },
        )
    return org_id


@router.get("")
async def list_clients(
    org_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    resolved_org = _resolve_org_id(request, org_id)
    await set_tenant_context(session, resolved_org)
    results = await _client_service.list_all(session)
    return [r.model_dump(by_alias=True) for r in results]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_client(
    org_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    resolved_org = _resolve_org_id(request, org_id)

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CLIENT_INVALID_BODY", "message": "Invalid JSON body"},
        )

    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "CLIENT_NAME_REQUIRED",
                "message": "Client name is required",
            },
        )

    import json

    settings_value = body.get("settings")
    record = Client(
        name=name,
        agency_id=resolved_org,
    )
    if settings_value:
        record.settings = settings_value

    await set_tenant_context(session, resolved_org)
    created = await _client_service.create(session, record)
    return created.model_dump(by_alias=True)


@router.get("/{client_id}")
async def get_client(
    org_id: str,
    client_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    resolved_org = _resolve_org_id(request, org_id)
    await set_tenant_context(session, resolved_org)
    result = await _client_service.get_by_id(session, client_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CLIENT_NOT_FOUND", "message": "Client not found"},
        )
    return result.model_dump(by_alias=True)


@router.patch("/{client_id}")
async def update_client(
    org_id: str,
    client_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    resolved_org = _resolve_org_id(request, org_id)

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CLIENT_INVALID_BODY", "message": "Invalid JSON body"},
        )

    await set_tenant_context(session, resolved_org)
    result = await _client_service.get_by_id(session, client_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CLIENT_NOT_FOUND", "message": "Client not found"},
        )

    if "name" in body:
        result.name = body["name"]
    if "settings" in body:
        result.settings = body["settings"]

    updated = await _client_service.update(session, result)
    return updated.model_dump(by_alias=True)


@router.delete("/{client_id}")
async def delete_client(
    org_id: str,
    client_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    resolved_org = _resolve_org_id(request, org_id)
    await set_tenant_context(session, resolved_org)

    result = await _client_service.get_by_id(session, client_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CLIENT_NOT_FOUND", "message": "Client not found"},
        )

    await _client_service.hard_delete(session, client_id)
    return {"success": True}
