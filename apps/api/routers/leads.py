"""Lead management API endpoints.

Provides custom fields management for hyper-personalization (Story 3.4).
"""

from fastapi import APIRouter, Depends
from pydantic import AliasGenerator, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session as get_db
from dependencies.org_context import get_current_org_id
from middleware.namespace_guard import verify_namespace_access
from schemas.variable_injection import CustomFieldsUpdateRequest
from services.shared_queries import set_rls_context, load_lead_for_context

router = APIRouter(tags=["Leads"])


class CustomFieldsResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=AliasGenerator(to_camel),
    )

    custom_fields: dict | None


@router.patch("/{lead_id}/custom-fields", response_model=CustomFieldsResponse)
async def update_custom_fields(
    lead_id: int,
    request_body: CustomFieldsUpdateRequest,
    session: AsyncSession = Depends(get_db),
    org_id: str = Depends(get_current_org_id),
):
    org_id = await verify_namespace_access(session=session, org_id=org_id)
    await set_rls_context(session, org_id)
    lead = await load_lead_for_context(session, lead_id, org_id, for_update=True)
    merged = {**(lead.custom_fields or {}), **request_body.custom_fields}
    lead.custom_fields = merged
    session.add(lead)
    await session.commit()
    await session.refresh(lead)
    return CustomFieldsResponse(custom_fields=lead.custom_fields)


@router.delete(
    "/{lead_id}/custom-fields/{field_name}", response_model=CustomFieldsResponse
)
async def delete_custom_field(
    lead_id: int,
    field_name: str,
    session: AsyncSession = Depends(get_db),
    org_id: str = Depends(get_current_org_id),
):
    org_id = await verify_namespace_access(session=session, org_id=org_id)
    await set_rls_context(session, org_id)
    lead = await load_lead_for_context(session, lead_id, org_id, for_update=True)
    fields = dict(lead.custom_fields or {})
    if field_name in fields:
        del fields[field_name]
        lead.custom_fields = fields
        session.add(lead)
        await session.commit()
        await session.refresh(lead)
    return CustomFieldsResponse(custom_fields=lead.custom_fields)
