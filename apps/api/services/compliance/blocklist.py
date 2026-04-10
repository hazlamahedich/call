from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.session import set_tenant_context
from models.blocklist_entry import BlocklistEntry

logger = logging.getLogger(__name__)


async def check_tenant_blocklist(
    session: AsyncSession,
    phone_number: str,
    org_id: str,
) -> Optional[BlocklistEntry]:
    await set_tenant_context(session, org_id)
    result = await session.execute(
        text(
            "SELECT id, org_id, phone_number, source, reason, lead_id, "
            "auto_blocked_at, expires_at, created_at, updated_at, soft_delete "
            "FROM blocklist_entries "
            "WHERE org_id = :org_id AND phone_number = :phone "
            "AND soft_delete = false "
            "AND (expires_at IS NULL OR expires_at > NOW()) "
            "LIMIT 1"
        ),
        {"org_id": org_id, "phone": phone_number},
    )
    row = result.first()
    if not row:
        return None
    return BlocklistEntry.model_construct(
        id=row[0],
        org_id=row[1],
        phone_number=row[2],
        source=row[3],
        reason=row[4],
        lead_id=row[5],
        auto_blocked_at=row[6],
        expires_at=row[7],
        created_at=row[8],
        updated_at=row[9],
        soft_delete=row[10],
    )


async def add_to_blocklist(
    session: AsyncSession,
    org_id: str,
    phone_number: str,
    source: str,
    reason: Optional[str] = None,
    lead_id: Optional[int] = None,
    expires_at: Optional[datetime] = None,
) -> BlocklistEntry:
    await set_tenant_context(session, org_id)
    result = await session.execute(
        text(
            "INSERT INTO blocklist_entries (org_id, phone_number, source, reason, lead_id, auto_blocked_at, expires_at) "
            "VALUES (:org_id, :phone, :source, :reason, :lead_id, :auto_blocked_at, :expires_at) "
            "ON CONFLICT (org_id, phone_number) DO UPDATE SET "
            "source = EXCLUDED.source, "
            "reason = EXCLUDED.reason, "
            "lead_id = EXCLUDED.lead_id, "
            "auto_blocked_at = EXCLUDED.auto_blocked_at, "
            "expires_at = EXCLUDED.expires_at, "
            "updated_at = NOW() "
            "RETURNING id, org_id, phone_number, source, reason, lead_id, "
            "auto_blocked_at, expires_at, created_at, updated_at, soft_delete"
        ),
        {
            "org_id": org_id,
            "phone": phone_number,
            "source": source,
            "reason": reason,
            "lead_id": lead_id,
            "auto_blocked_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
        },
    )
    row = result.first()
    await session.flush()
    if not row:
        raise RuntimeError(
            f"blocklist upsert returned no row for {org_id}/{phone_number}"
        )
    return BlocklistEntry.model_construct(
        id=row[0],
        org_id=row[1],
        phone_number=row[2],
        source=row[3],
        reason=row[4],
        lead_id=row[5],
        auto_blocked_at=row[6],
        expires_at=row[7],
        created_at=row[8],
        updated_at=row[9],
        soft_delete=row[10],
    )


async def remove_from_blocklist(
    session: AsyncSession,
    org_id: str,
    phone_number: str,
) -> bool:
    await set_tenant_context(session, org_id)
    result = await session.execute(
        text(
            "UPDATE blocklist_entries SET soft_delete = true, updated_at = NOW() "
            "WHERE org_id = :org_id AND phone_number = :phone AND soft_delete = false"
        ),
        {"org_id": org_id, "phone": phone_number},
    )
    await session.flush()
    return result.rowcount > 0
